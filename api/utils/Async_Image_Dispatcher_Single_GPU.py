import asyncio
import aiohttp
from datetime import datetime
import sys, os, json, pytz
import traceback

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from rabbitmq import RabbitMQ
from helper import getConfigInfo
from classes.Image_enhace import ImageEnhacement

gpu_ip = sys.argv[1]
port = sys.argv[2]
if gpu_ip == "" or port == "":
    print("No GPU IP or port passed")
    exit(1)

gpu_url = f"http://{gpu_ip}:{port}"
subscribe_queue = 'image_enhance_process'

def validate_gpu(gpu_url):
    import requests
    try:
        response = requests.get(f"{gpu_url}/health")
        return response.status_code == 200
    except:
        return False

async def process_message(session, gpu_url, body):
    try:
        queue_data = json.loads(body)
        rabbitmq_con = RabbitMQ()
        image_enhacement = ImageEnhacement()

        if "message" in queue_data:
            msg = queue_data["message"]
            if "product_url" in msg and "docid" in msg:
                async with session.post(f"{gpu_url}/v1/img_enhance", json=msg) as resp:
                    response_data = await resp.json()

                if response_data.get("error_code") == 0:
                    msg["gpu_res"] = response_data
                    msg["purge"] = 1
                    msg["action"] = "update"
                    input_data = {
                        "data": {
                            "message": msg,
                            "queue_name": "image_enhance_update"
                        }
                    }
                    status, msg = image_enhacement.PushToQueue(input_data)
                    print(status)
                else:
                    print("GPU Error response")
            else:
                print("Invalid message structure")
                await post_error(queue_data, rabbitmq_con)
        else:
            print("Missing 'message' field")
            await post_error(queue_data, rabbitmq_con)

        current_date = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
        print(current_date)

        return True

    except Exception as e:
        print("Exception during async message processing:", str(e))
        traceback.print_exc()
        return False

async def post_error(data, rabbitmq_con):
    errorData = {
        "queue_name": f"error.{subscribe_queue}",
        **data
    }
    rabbitmq_con.postQueue(errorData)

async def consume():
    rabbit_mq = RabbitMQ()
    connectServer = getConfigInfo('rabbitmq_server1')
    connection = rabbit_mq.createConnection(connectServer)
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)

    image_enhacement = ImageEnhacement()
    queue = channel.queue_declare(queue=subscribe_queue, passive=False, durable=True)

    async with aiohttp.ClientSession() as session:
        loop = asyncio.get_running_loop()
        def on_message(ch, method, properties, body):
            asyncio.run_coroutine_threadsafe(
                handle_and_ack(ch, method, body, session), loop
            )

        channel.basic_consume(queue=subscribe_queue, on_message_callback=on_message)
        print("[*] Waiting for messages. Press CTRL+C to exit.")
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()

async def handle_and_ack(ch, method, body, session):
    success = await process_message(session, gpu_url, body)
    if success:
        ch.basic_ack(delivery_tag=method.delivery_tag)
    else:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

if __name__ == "__main__":
    if validate_gpu(gpu_url):
        print("GPU Health OK")
        asyncio.run(consume())
    else:
        print("GPU health check failed")
        exit(1)
