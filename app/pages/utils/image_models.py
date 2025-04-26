# pip install accelerate
from __future__ import annotations

import os

import clip
import torch
from huggingface_hub import login
from PIL import Image
from transformers import AutoProcessor
from transformers import Gemma3ForConditionalGeneration

HF_TOKEN = os.environ.get("HF_TOKEN")
assert HF_TOKEN is not None
login(os.environ.get("HF_TOKEN"), new_session=True)

GEMMA_MODEL_ID = "google/gemma-3-4b-it"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_clip_model(model_id=None):
    model, preprocess = clip.load("ViT-B/32", device=DEVICE)
    return model, preprocess


def generate_image_vector(image, model, preprocess):
    image = preprocess(image).unsqueeze(0).to(DEVICE)
    image_features = model.encode_image(image)
    return image_features


def generate_text_vector(texts, model):
    texts_tokens = clip.tokenize(texts).to(DEVICE)
    texts_features = model.encode_text(texts_tokens)
    return texts_features


def load_gemma_model(model_id=None):
    model_id = model_id if model_id else GEMMA_MODEL_ID
    model = Gemma3ForConditionalGeneration.from_pretrained(
        model_id,
        device_map=DEVICE,
        torch_dtype=torch.bfloat16,
    ).eval()
    processor = AutoProcessor.from_pretrained(GEMMA_MODEL_ID, use_fast=True)
    return model, processor


def generate_image_description(
    image: Image,
    model,
    processor,
    language: str = "spanish",
):
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": """
Role: You are an expert visual analyst and caption writer.
Audience: Your captions will be used by people searching for images or recalling personal memories.
Scenario: You receive an image and need to describe it clearly and efficiently.
Context: The description should aid in search indexing and memory recall by providing factual, visual details.
Expectation:
- Identify recognizable landmarks, monuments, or signs.
- Mention the setting (e.g., city, street, building type) and context (e.g., transportation, event).
- Include visible weather conditions or time of day if apparent (e.g., sunny, rainy, golden hour).
- Note any distinctive visual details (e.g., tram, café, graffiti, architecture style).
- Be concise, vivid, and accurate.
- Avoid subjective impressions or storytelling.
- Avoid any meta-description or references to the image itself.
Format: Only include one to two factual and descriptive sentences per image. Do not include anything else.
""",
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Describe the following image in {language}:",
                },
                {"type": "image", "image": image},
            ],
        },
    ]

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device, dtype=torch.bfloat16)

    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generation = model.generate(**inputs, max_new_tokens=100, do_sample=False)
        generation = generation[0][input_len:]

    decoded = processor.decode(generation, skip_special_tokens=True)
    return decoded


if __name__ == "__main__":
    example_image = "example-image.jpg"
    image = Image.open(example_image)
    model, processor = load_gemma_model()
    print(generate_image_description(image, model, processor))
