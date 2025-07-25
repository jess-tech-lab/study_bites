import re
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
    query_params = request.args.to_dict()
    print(f"Query Parameters: {query_params}")

    page = request.args.get('page', 0, type=int)
    isVegan = query_params.get('vegan', '').lower() == 'true'
    isWheelchair = query_params.get('wheelchair', '').lower() == 'true'
    isKidFriendly = query_params.get('kid_friendly', '').lower() == 'true'
    isBudget = query_params.get('budget', '').lower() == 'true'

    location = session.get('location')
    lat = location['latitude'] if location else 42.3149
    lng = location['longitude'] if location else -81.1496
    
    
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
        
        print("Tag filters being used:", ','.join(tag_filters)) # Log tag filters
        
        params = {
            'filter.tags': ','.join(tag_filters),
            'filter.location': f'{lat},{lng}',
            'filter.radius': 10,
            'limit': 500,  # Increased limit to ensure we have enough after filtering
            'offset': 0,
            'operator.filter.tags': 'intersection'
        }
        
        print("Full API parameters:", params)  # Log full parameters
        
        response = requests.get(f'{QLOO_BASE_URL}/search', headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            # print("API Response first result tags:", data.get('results', [{}])[0].get('tags', []) if data.get('results') else "No results")  # Log first result's tags
            print(len(data.get('results', [])))
            all_foods = []
            
            for restaurant in data.get('results', []):
                # Skip non-budget friendly places if budget preference is enabled
                # if preferences.get('budget'):
                #     price_level = restaurant.get('properties', {}).get('price_level')
                #     if price_level and price_level in ['$$$', '$$$$']:
                #         continue
                
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
            
            # Paginate the filtered results
            start_idx = page * 4
            end_idx = start_idx + 4
            current_page_foods = all_foods[start_idx:end_idx]
            total_pages = max(1, (len(all_foods) + 3) // 4)  # Ceiling division by 4
            
            return jsonify({
                'success': True,
                'foods': current_page_foods,
                'current_page': page,
                'total_pages': total_pages,
                'has_next': page < total_pages - 1,
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
        
        print(f"\nSearching for restaurant with entity_id: {entity_id}")  # Log entity ID
        
        try:
            response = requests.get(f'{self.base_url}/entities', headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            # print("Restaurant API response:", data)  # Log full response
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
    
# @app.route('/api/update-preferences', methods=['POST'])
# def update_preferences():
#     data = request.json
#     preferences = data.get('preferences', {})

#     session['preferences'] = {
#         'vegan': preferences.get('vegan', False),
#         'wheelchair': preferences.get('wheelchair', False),
#         'budget': preferences.get('budget', False),
#         'kid_friendly': preferences.get('kid_friendly', False)
#     }
#     return jsonify({'success': True, 'message': 'Preferences updated successfully'})


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
        print(f"\nFetching details for restaurant ID: {restaurant_id}")  # Log restaurant ID
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