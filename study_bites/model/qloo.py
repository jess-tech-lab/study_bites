import requests
import os

QLOO_BASE_URL = 'https://hackathon.api.qloo.com'
# API KEY
QLOO_API_KEY = os.environ.get('QLOO_API_KEY')
print(QLOO_API_KEY)

PAGE_SIZE = 4
TOTAL_SIZE = 20

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


