from flask import Flask, render_template, request, jsonify, session
import os
import sys
import uuid
import requests
import threading
import time
from study_bites.model.qloo import QLOOService, TOTAL_SIZE, PAGE_SIZE, QLOO_API_KEY, load_data
from study_bites.utils.ml import classify_image
from study_bites.utils.logger import logger

app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY')
logger.info(app.secret_key)

cache = {}  # key: "lat,lon" -> dict with raw, valid_flags, lock, done

qloo_service = QLOOService(QLOO_API_KEY)

@app.route('/api/food-options')
def get_food_options():
    query_params = request.args.to_dict()
    logger.info(f"Query Parameters: {query_params}")

    page = request.args.get('page', 0, type=int)
    isVegan = query_params.get('vegan', '').lower() == 'true'
    isWheelchair = query_params.get('wheelchair', '').lower() == 'true'
    isKidFriendly = query_params.get('kid_friendly', '').lower() == 'true'
    isBudget = query_params.get('budget', '').lower() == 'true'

    
    lat = round(request.args.get('lat', 0, type=float), 4)
    lng = round(request.args.get('lng', 0, type=float), 4)
    
    latlng_key = f"{lat},{lng}_{int(isVegan)}{int(isWheelchair)}{int(isKidFriendly)}{int(isBudget)}"
    logger.info(latlng_key)

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
                logger.info("[Location "+food_item['name']+" with image "+food_item['image']+" is evaulated to be a valid image "+str(valid)+"]")
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
                logger.info("Valid items " + str(len(valid_items)))
                # Invalid/unvalidated items
                invalid_items = [item for item, flag in zip(raw, flags) if flag is not True]
                logger.info("Invalid items " + str(len(invalid_items)))

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

    logger.info("+++++Get food id "+str(food_id))
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
        logger.error(f"Error getting restaurants: {e}")
        return jsonify({
            'success': False,
            'alternatives': [],
            'error': str(e)
        }), 500

@app.route('/api/restaurant/<restaurant_id>')
def get_restaurant_detail(restaurant_id):
    try:
        logger.info(f"\nFetching details for restaurant ID: {restaurant_id}")  
        result = qloo_service.get_restaurant_details(restaurant_id)
        if result:
            logger.info("Restaurant tags: %s", result.get('tags', []))  # Log restaurant tags
            return jsonify({'success': True, 'restaurant': result})
        else:
            return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
    except Exception as e:
        logger.error(f"Error getting restaurant details: {e}")
        return jsonify({'success': False, 'message': 'Error getting restaurant details'}), 500

if __name__ == '__main__':
    app.run(debug=True)