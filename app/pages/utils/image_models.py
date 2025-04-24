# pip install accelerate
from transformers import AutoProcessor, Gemma3ForConditionalGeneration
from PIL import Image
from io import BytesIO
import torch

GEMMA_MODEL_ID = "google/gemma-3-4b-it"
GEMMA_MODEL = Gemma3ForConditionalGeneration.from_pretrained(
    GEMMA_MODEL_ID, device_map="auto"
).eval()
GEMMA_PROCESSOR = AutoProcessor.from_pretrained(GEMMA_MODEL_ID, use_fast=True)


def generate_image_description(image: Image):
    messages = [
        {
            "role": "system",
            # TODO: Improve system prompt template
            "content": [{"type": "text", "text": "You are a helpful assistant."}]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                # TODO: Improve context prompt template
                {"type": "text", "text": "Describe this image in detail."}
            ]
        }
    ]

    inputs = GEMMA_PROCESSOR.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt"
    ).to(GEMMA_MODEL.device, dtype=torch.bfloat16)

    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generation = GEMMA_MODEL.generate(**inputs, max_new_tokens=100, do_sample=False)
        generation = generation[0][input_len:]

    decoded = GEMMA_PROCESSOR.decode(generation, skip_special_tokens=True)
    return decoded


if __name__ == "__main__":
    example_image = "example-image.jpg"
    image = Image.open(example_image)
    print(generate_image_description(image))