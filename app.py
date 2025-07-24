from flask import Flask, render_template, request, jsonify, session
import os
from datetime import datetime
import json
import math
import uuid
from jinja2.utils import F
import requests

app = Flask(__name__)
app.secret_key = 'pwiefj0139qwekfajefw3ptehfajwefoijwajedof2oi3ejwdsocj'

# API HERE
QLOO_API_KEY = 'UKS35G0e_HzNqCu1MoVk8LuDUB8JwCnFW0tOU2eQmM0'
QLOO_BASE_URL = 'https://hackathon.api.qloo.com'

@app.route('/api/food-options')
def get_food_options():
    page = request.args.get('page', 0, type=int)

    location = session.get('location')
    lat = location['latitude'] if location else 42.3149
    lng = location['longitude'] if location else -81.1496
    
    try:
        headers = {
            'X-API-Key': QLOO_API_KEY,
            'accept': 'application/json'
        }
        
        params = {
            'query': 'restaurant',
            'filter.tags': 'urn:tag:genre:restaurant',
            'filter.location': f'{lat},{lng}',
            'filter.radius': 10,
            'limit': 4,
            'offset': page * 4
        }
        
        response = requests.get(f'{QLOO_BASE_URL}/search', headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            foods = []
            
            for restaurant in data.get('results', []):
                image_url = None
                if restaurant.get('properties', {}).get('image'):
                    image_url = restaurant['properties']['image'].get('url')
                
                food_item = {
                    'id': restaurant.get('entity_id', f'food_{len(foods)}'),
                    'name': restaurant.get('name', 'Restaurant'),
                    'desc': restaurant.get('disambiguation', 'Great food'),
                    'image': image_url,
                    'restaurant_id': restaurant.get('entity_id')
                }
                foods.append(food_item)
            
            return jsonify({
                'success': True,
                'foods': foods,
                'current_page': page,
                'total_pages': 10,  
                'has_next': len(foods) == 4,
                'has_prev': page > 0
            })
            
    except Exception as e:
        print(f"Error: {e}")
    
    return jsonify({'success': False, 'error': 'Failed to load options'}), 500

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
        
        try:
            response = requests.get(f'{self.base_url}/entities', headers=headers, params=params)
            response.raise_for_status()
            return response.json()
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
        session['preferences'] = {
            'vegan': True,
            'wheelchair': True,
            'budget': True,
            'kid_friendly': True
        }
    return render_template('index.html')

@app.route('/api/update-location', methods=['POST'])
def update_location():
    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')
    if lat and lng:
        session['location'] = {
            'latitude': float(lat),
            'longitude': float(lng),
            'updated_at': datetime.now().isoformat()
        }
        return jsonify({'success': True, 'message': 'Location updated successfully'})
    return jsonify({'success': False, 'error': 'Invalid location data'})
    
@app.route('/api/update-preferences', methods=['POST'])
def update_preferences():
    data = request.json
    preferences = data.get('preferences', {})

    session['preferences'] = {
        'vegan': preferences.get('vegan', False),
        'wheelchair': preferences.get('wheelchair', False),
        'budget': preferences.get('budget', False),
        'kid_friendly': preferences.get('kid_friendly', False)
    }
    return jsonify({'success': True, 'message': 'Preferences updated successfully'})


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
        result = qloo_service.get_restaurant_details(restaurant_id)
        if result:
            return jsonify({'success': True, 'restaurant': result})
        else:
            return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
    except Exception as e:
        print(f"Error getting restaurant details: {e}")
        return jsonify({'success': False, 'message': 'Error getting restaurant details'}), 500

if __name__ == '__main__':
    app.run(debug=True)