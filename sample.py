import os
import argparse
from classes.RealESR import ModelHandler  # Adjust path if needed

def run_inference(args):
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

    # Initialize model handler
    model_list = ['RealESRNet_x4plus', 'RealESRGAN_x4plus', 'GFPGANer']
    model_handler = ModelHandler(model_list)
    model_handler.set_memory_limit(args.memory_limit)

    # Prepare input
    input_data = {
        "product_url": args.image_url,
        "org_product_url": args.org_image_url,
        "image_type": args.image_type,
        "force": args.force
    }

    # Run model
    enhanced_image, message, err, status_code = model_handler.process(input_data)

    if enhanced_image is None:
        print(f"[❌] Failed: {message}\nError: {err}")
    else:
        print(f"[✅] Success: {message}")
        output_path = f"{args.output_dir}/enhanced.jpg"
        with open(output_path, "wb") as f:
            f.write(enhanced_image)
        print(f"[💾] Saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Local Image Enhancement")
    parser.add_argument("--image_url", required=True, help="Output destination image path (used for naming only)")
    parser.add_argument("--org_image_url", required=True, help="Original image URL")
    parser.add_argument("--image_type", default="general", help="Image type (e.g., 'general')")
    parser.add_argument("--force", type=int, default=0, help="Force enhancement (1 or 0)")
    parser.add_argument("--memory_limit", type=int, default=4, help="GPU memory limit in GB")
    parser.add_argument("--output_dir", default=".", help="Where to save enhanced image")
    args = parser.parse_args()
    run_inference(args)
