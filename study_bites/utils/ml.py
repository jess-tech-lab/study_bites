from sre_parse import Tokenizer
from transformers import CLIPModel, CLIPImageProcessor, AutoTokenizer, CLIPProcessor
from io import BytesIO
from PIL import Image

import torch
import requests
from study_bites.utils.logger import logger

labels = [
    "meal", 
    "restaurant interior", 
    "restaurant exterior", "storefront",
    "chef"
]

model = None
tokenizer = None
image_processor = None
initialized = False

def initialize_model():
    global initialized, model, tokenizer, image_processor

    if not initialized:
        MODEL_ID = "zer0int/CLIP-GmP-ViT-L-14"
        model = CLIPModel.from_pretrained(MODEL_ID)
        # Load processor (includes tokenizer + image processor)
        processor = CLIPProcessor.from_pretrained(MODEL_ID)
        tokenizer = processor.tokenizer
        image_processor = processor.feature_extractor
        
        initialized = True
        logger.info("_____Hugging Face ML model initialized")

def classify_image(image_url):
    if not image_url:
        logger.info("+++++++++++Invalid image url")
        return False

    images = []

    initialize_model()

    # Load images from URLs
    response = requests.get(image_url)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content)).convert("RGB")
    images.append(img)

    # Move model and inputs to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Preprocess labels and images
    text_inputs = tokenizer(labels, return_tensors="pt", padding=True).to(device)
    image_inputs = image_processor(images=images, return_tensors="pt").to(device)

    # Inference
    with torch.no_grad():
        outputs = model(**text_inputs, **image_inputs)

    # Get probabilities
    logits_per_image = outputs.logits_per_image  
    probs = logits_per_image.softmax(dim=1)  

    top_probs, top_idxs = probs.topk(1, dim=1)

    result = {
        "image": image_url,
        "label": labels[top_idxs[0].item()],
        "score": round(top_probs[0].item(), 4)
    }
    # logger.info(result)

    if result['label'] != "chef" and result['score'] > 0.75:
        return True
    else:
        return False