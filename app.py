import re
from flask import Flask, render_template, request, jsonify, session
import os
from datetime import datetime
import json
import math
import uuid
from jinja2.utils import F
import requests
from transformers import CLIPModel, CLIPImageProcessor, AutoTokenizer, CLIPProcessor
from concurrent.futures import ThreadPoolExecutor
import torch
from PIL import Image
from io import BytesIO
import threading
import time

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
print(app.secret_key)

# API HERE
QLOO_API_KEY = os.environ.get('QLOO_API_KEY')
print(QLOO_API_KEY)
QLOO_BASE_URL = 'https://hackathon.api.qloo.com'

# CLIP model
MODEL_ID = "zer0int/CLIP-GmP-ViT-L-14"
model = CLIPModel.from_pretrained(MODEL_ID)
# Load processor (includes tokenizer + image processor)
processor = CLIPProcessor.from_pretrained(MODEL_ID)
tokenizer = processor.tokenizer
image_processor = processor.feature_extractor

PAGE_SIZE = 4
TOTAL_SIZE = 20
cache = {}  # key: "lat,lon" -> dict with raw, valid_flags, lock, done

labels = [
    "meal", 
    "restaurant interior", 
    "restaurant exterior", "storefront",
    "chef"
]
def classify_image(image_url):
    if not image_url:
        print("+++++++++++Invalid image url")
        return False

    images = []

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
    # print(result)

    if result['label'] != "chef" and result['score'] > 0.75:
        return True
    else:
        return False

@app.route('/api/food-options')
def get_food_options():
    query_params = request.args.to_dict()
    print(f"Query Parameters: {query_params}")

    page = request.args.get('page', 0, type=int)
    isVegan = query_params.get('vegan', '').lower() == 'true'
    isWheelchair = query_params.get('wheelchair', '').lower() == 'true'
    isKidFriendly = query_params.get('kid_friendly', '').lower() == 'true'
    isBudget = query_params.get('budget', '').lower() == 'true'

    
    lat = round(request.args.get('lat', 0, type=float), 4)
    lng = round(request.args.get('lng', 0, type=float), 4)
    
    latlng_key = f"{lat},{lng}_{int(isVegan)}{int(isWheelchair)}{int(isKidFriendly)}{int(isBudget)}"
    print(latlng_key)

    if latlng_key not in cache:
        food_items = load_data(lat, lng, isVegan, isWheelchair, isKidFriendly, isBudget)

        cache[latlng_key] = {
            "raw": food_items,
            "valid_flags": [None] * TOTAL_SIZE,  # None = unvalidated, True = valid, False = invalid
            "lock": threading.Lock(),
            "done": False,
        }

        def worker():
            index = 0
            for food_item in food_items:
                valid = classify_image(food_item['image'])
                print("Location "+food_item['name']+" with image "+food_item['image']+" is evaulated to be a valid image ", valid)
                with cache[latlng_key]["lock"]:
                    cache[latlng_key]["valid_flags"][index] = valid
                    index = index+1
            with cache[latlng_key]["lock"]:
                cache[latlng_key]["done"] = True

        threading.Thread(target=worker, daemon=True).start()

    required_valid = min((page + 1) * PAGE_SIZE, TOTAL_SIZE)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    while True:
        with cache[latlng_key]["lock"]:
            flags = cache[latlng_key]["valid_flags"]
            done = cache[latlng_key]["done"]
            valid_count = sum(1 for v in flags if v is True)

            # Check if enough validated items for requested page, or all validation done
            if valid_count >= required_valid or done:
                raw = cache[latlng_key]["raw"]

                # Valid items (preserve original order)
                valid_items = [item for item, flag in zip(raw, flags) if flag is True]
                print("valid items ", len(valid_items))
                # Invalid/unvalidated items
                invalid_items = [item for item, flag in zip(raw, flags) if flag is not True]
                print("Invalid items", len(invalid_items))

                combined = valid_items + invalid_items

                # Defensive slice bounds
                if start >= len(combined):
                    return jsonify({"error": "Page out of range"}), 404

                page_items = combined[start:end]
                total_pages = max(1, (len(raw) + 3) // 4)  

                return jsonify({
                    'success': True,
                    "current_page": page,
                    "foods": page_items,
                    'total_pages': total_pages,
                    'has_next': page < total_pages - 1,
                    'has_prev': page > 0  
                })

        time.sleep(0.2)


def load_data(lat, lng, isVegan, isWheelchair, isKidFriendly, isBudget):
    try:
        headers = {
            'X-API-Key': QLOO_API_KEY,
            'accept': 'application/json'
        }
        
        # Build tag filters based on preferences
        tag_filters = ['urn:tag:genre:restaurant']
        
        if isVegan:
            tag_filters.append('urn:tag:offerings:vegan_options')
        if isWheelchair:
            tag_filters.append('urn:tag:accessibility:wheelchair_accessible_entrance')
        if isBudget:
            tag_filters.append('urn:tag:cost_description:inexpensive')
        if isKidFriendly:
            tag_filters.append('urn:tag:children:good_for_kids')
        
        # print("Tag filters being used:", ','.join(tag_filters))
        
        params = {
            'filter.tags': ','.join(tag_filters),
            'filter.location': f'{lat},{lng}',
            'filter.radius': 50,
            'take': TOTAL_SIZE,  
            'page': 1,
            'operator.filter.tags': 'intersection'
        }
        
        print("Full API parameters:", params)  
        
        response = requests.get(f'{QLOO_BASE_URL}/search', headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            # print("API Response first result tags:", data.get('results', [{}])[0].get('tags', []) if data.get('results') else "No results") 
            print(len(data.get('results', [])))
            all_foods = []
            
            for restaurant in data.get('results', []):                
                image_url = None
                if restaurant.get('properties', {}).get('image'):
                    image_url = restaurant['properties']['image'].get('url')
                
                food_item = {
                    'id': restaurant.get('entity_id', f'food_{len(all_foods)}'),
                    'name': restaurant.get('name', 'Restaurant'),
                    'desc': restaurant.get('disambiguation', 'Great food'),
                    'image': image_url,
                    'restaurant_id': restaurant.get('entity_id')
                }
                all_foods.append(food_item)

            return all_foods
        else:
            print(response)                           
    except Exception as e:
        print(f"Error: {e}")
    
    return None

class QLOOService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = QLOO_BASE_URL

    def search_restaurants(self, entity_id):
        """
        Get restaurants based on location and filters
        """
        headers = {
            'X-API-Key': self.api_key,
            'accept': 'application/json'
        }
        
        params = {
            'entity_ids': entity_id
        }
        
        print(f"\nSearching for restaurant with entity_id: {entity_id}") 
        
        try:
            response = requests.get(f'{self.base_url}/entities', headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            # print("Restaurant API response:", data)  
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error calling API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            return None

    def get_restaurant_details(self, restaurant_id):
        """
        Get details for a restaurant
        """
        headers = {
            'X-API-Key': self.api_key,
            'accept': 'application/json'
        }
        try:
            response = requests.get(f'{self.base_url}/entities/{restaurant_id}', headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting restaurant details: {e}")
            return None

qloo_service = QLOOService(QLOO_API_KEY)

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/api/restaurants')
def get_restaurants():
    food_id = request.args.get('food_id')
    if not food_id:
        return jsonify({'success': False, 'error': 'Food ID is required'}), 400

    location = session.get('location') 
    if not location:
        return jsonify({'success': False, 'error': 'Location not set'}), 400

    print("+++++Get food id "+str(food_id))
    try:
        results = qloo_service.search_restaurants(
            entity_id=food_id
        )

        if results and 'results' in results: 
            restaurants = []
            for item in results['results']:
                image_url = None
                if 'properties' in item and 'image' in item['properties']:
                    image_url = item['properties']['image'].get('url')
                
                restaurant = {
                    'id': item.get('entity_id'),
                    'name': item.get('name'),
                    'business_rating': item.get('properties', {}).get('business_rating'),
                    'description': item.get('disambiguation', ''),
                    'address': item.get('properties', {}).get('address'),
                    'distance': item.get('properties', {}).get('distance'),
                    'price_range': item.get('properties', {}).get('price_level'),
                    'phone': item.get('properties', {}).get('phone'),
                    'hours': item.get('properties', {}).get('hours'),
                    'image_url': image_url,
                    'location': item.get('location', {}),
                    'tags': item.get('tags', []),
                    'properties': item.get('properties', {})
                }
                restaurants.append(restaurant)

            if restaurants:
                return jsonify({
                    'success': True,
                    'restaurant': restaurants[0], 
                    'alternatives': restaurants[1:5] if len(restaurants) > 1 else []
                })
            
        return jsonify({'success': False, 'alternatives': [],'error': 'No restaurants found'}), 404

    except Exception as e:
        print(f"Error getting restaurants: {e}")
        return jsonify({
            'success': False,
            'alternatives': [],
            'error': str(e)
        }), 500

@app.route('/api/restaurant/<restaurant_id>')
def get_restaurant_detail(restaurant_id):
    try:
        print(f"\nFetching details for restaurant ID: {restaurant_id}")  
        result = qloo_service.get_restaurant_details(restaurant_id)
        if result:
            print("Restaurant tags:", result.get('tags', []))  # Log restaurant tags
            return jsonify({'success': True, 'restaurant': result})
        else:
            return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
    except Exception as e:
        print(f"Error getting restaurant details: {e}")
        return jsonify({'success': False, 'message': 'Error getting restaurant details'}), 500

if __name__ == '__main__':
    app.run(debug=True)