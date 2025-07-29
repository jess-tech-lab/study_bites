let currentFoodPage = 0;
let selectedFood = null;
let userLocation = null;
let totalFoodPages = 0;
let currentFoodData = [];
let userRadius = 25;
let isLoading = false

document.addEventListener('DOMContentLoaded', function() {
    console.log('StudyBites app initializing...');
    initializeSession();
    getUserLocation();
    loadFoodOptions(0);
    setupFilterListeners();
    setupRadiusControl();
    setupErrorHandling();
    setupAnimations();
    setupKeyboardShortcuts();
    
    // Initialize navigation buttons
    updateNavigationButtons(false, true);
});

function initializeSession() {
    if (!sessionStorage.getItem('sessionId')) {
        const sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
        sessionStorage.setItem('sessionId', sessionId);
    }
    
    const defaultPreferences = {
        vegan: true,
        wheelchair: true,
        budget: true,
        kid_friendly: true
    };

    Object.keys(defaultPreferences).forEach(key => {
        const checkbox = document.getElementById(key === 'kid_friendly' ? 'kidfriendly' : key);
        if (checkbox) {
            checkbox.checked = defaultPreferences[key];
        }
    });
}

function getUserLocation(callback) {
    const locationText = document.querySelector('.location-badge span:last-child');
    if (!locationText) {
        console.error('Location display element not found');
        useDefaultLocation();
        return;
    }
    
    if (navigator.geolocation) {
        locationText.textContent = 'Getting location...';
        addLoadingSpinner(locationText);

        navigator.geolocation.getCurrentPosition(
            function(position) {
                userLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                };
                console.log('Location acquired:', userLocation);
                callback(userLocation);  
                // updateServerLocation(userLocation);
                reverseGeocode(userLocation.latitude, userLocation.longitude);
                removeLoadingSpinner(locationText);

                if (selectedFood) {
                    loadRestaurant(selectedFood);
                }
            },
            function(error) {
                console.error('Error getting location:', error);
                handleLocationError(error);
                removeLoadingSpinner(locationText);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000
            }
        );
    } else {
        locationText.textContent = 'Geolocation not supported';
        useDefaultLocation();
    }
}

function handleLocationError(error) {
    const locationText = document.querySelector('.location-badge span:last-child');
    let errorMessage = 'Location unavailable';

    switch(error.code) {
        case error.PERMISSION_DENIED:
            errorMessage = 'Location denied';
            break;
        case error.POSITION_UNAVAILABLE:
            errorMessage = 'Location unavailable';
            break;
        case error.TIMEOUT:
            errorMessage = 'Location timeout';
            break;
    }

    if (locationText) locationText.textContent = errorMessage;
    useDefaultLocation();
    showLocationPermissionPrompt();
}

function useDefaultLocation() {
    userLocation = { 
        latitude: 42.3149, 
        longitude: -81.1496,
        isDefault: true 
    };
    // updateServerLocation(userLocation);
    
    const locationText = document.querySelector('.location-badge span:last-child');
    if (locationText) locationText.textContent = 'St. Thomas, ON';
}

function showLocationPermissionPrompt() {
    const prompt = document.createElement('div');
    prompt.className = 'location-prompt';
    prompt.innerHTML = `
        <div class="prompt-content">
            <p>Enable location for better restaurant recommendations</p>
            <button onclick="requestLocationAgain()" class="retry-location-btn">Enable Location</button>
            <button onclick="dismissLocationPrompt()" class="dismiss-btn">Continue without location</button>
        </div>
    `;
    document.body.appendChild(prompt);

    setTimeout(() => {
        dismissLocationPrompt();
    }, 10000);
}

function requestLocationAgain() {
    dismissLocationPrompt();
    getUserLocation();
}

function dismissLocationPrompt() {
    const prompt = document.querySelector('.location-prompt');
    if (prompt) {
        prompt.remove();
    }
}

function reverseGeocode(lat, lng) {
    const locationText = document.querySelector('.location-badge span:last-child');
    if (locationText) locationText.textContent = `${lat.toFixed(2)}, ${lng.toFixed(2)}`;
    
    const geocodeUrl = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=en`;
    
    fetch(geocodeUrl)
        .then(response => {
            if (!response.ok) throw new Error('Geocoding failed');
            return response.json();
        })
        .then(data => {
            let displayText = '';
            if (data.city && data.principalSubdivision) {
                displayText = `${data.city}, ${data.principalSubdivision}`;
            } else if (data.locality) {
                displayText = data.locality;
            } else if (data.countryName) {
                displayText = data.countryName;
            } else {
                throw new Error('No location data');
            }
            if (locationText) locationText.textContent = displayText;
        })
        .catch(error => {
            console.log('Geocoding failed, using coordinates:', error);
        });
}

// Filters
function setupFilterListeners() {
    document.querySelectorAll('.filter-input').forEach(input => {
        input.addEventListener('change', debounce(function() {
            console.log('Filter changed:', this.id, this.checked);
            loadFoodOptions(0);
        }, 300));
    });
}

function setupRadiusControl() {
    const radiusSlider = document.getElementById('radiusSlider');
    const radiusValue = document.getElementById('radiusValue');

    if (radiusSlider && radiusValue) {
        radiusSlider.value = userRadius;
        radiusValue.textContent = `${userRadius} km`;

        radiusSlider.addEventListener('input', debounce(function() {
            userRadius = parseInt(this.value);
            radiusValue.textContent = `${userRadius} km`;

            if (userLocation) {
                // updateServerLocation(userLocation);
            }
            if (selectedFood) {
                loadRestaurant(selectedFood);
            }
        }, 500));
    }
}

function loadFoodOptions(page) {
    if (isLoading) return;
    isLoading = true;
    const foodLoading = document.getElementById('foodLoading');
    const foodGrid = document.getElementById('foodGrid');
    const sessionId = sessionStorage.getItem('sessionId');
    
    // Get current preferences
    const preferences = {
        vegan: document.getElementById('vegan').checked,
        wheelchair: document.getElementById('wheelchair').checked,
        budget: document.getElementById('budget').checked,
        kid_friendly: document.getElementById('kidfriendly').checked
    };
    
    console.log('Loading food options with preferences:', preferences);
    
    if (foodLoading) foodLoading.classList.add('show');
    foodGrid.style.opacity = '0.5';
    foodGrid.style.transform = 'translateY(10px)';

    getUserLocation(function(location) {
        if (location) {
            // Add preferences to query parameters
            const params = new URLSearchParams({
                lat: location.latitude,
                lng: location.longitude,
                page: page,
                vegan: preferences.vegan,
                wheelchair: preferences.wheelchair,
                budget: preferences.budget,
                kid_friendly: preferences.kid_friendly
            });

            fetch(`/api/food-options?${params.toString()}`, {
                headers: {
                    'X-Session-ID': sessionId
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    console.log('Received food options:', data.foods);
                    currentFoodData = data.foods;
                    currentFoodPage = data.current_page;
                    totalFoodPages = data.total_pages || 3; 
                    
                    renderFoodCards(currentFoodData);
                    
                    // Update navigation based on current page
                    const hasPrev = currentFoodPage > 0;
                    const hasNext = currentFoodPage < totalFoodPages - 1;
                    updateNavigationButtons(hasPrev, hasNext);
                    updatePageIndicator();
                    
                    setTimeout(() => {
                        foodGrid.style.transform = 'translateY(0)';
                    }, 100);
                } else {
                    throw new Error(data.error || 'Failed to load food options');
                }
            })
            .catch(error => {
                console.error('Error loading food options:', error);
                showError('Failed to load food options');
            })
            .finally(() => {
                isLoading = false;
                if (foodLoading) foodLoading.classList.remove('show');
                foodGrid.style.opacity = '1';
            });

        }
    });
}

function renderFoodCards(foods) {
    const foodGrid = document.getElementById('foodGrid');
    foodGrid.innerHTML = '';
    
    // Only render up to 4 food cards
    foods.slice(0, 4).forEach((food, index) => {
        const card = document.createElement('div');
        card.className = 'food-card';
        card.dataset.food = food.id;
        card.style.animationDelay = `${index * 0.1}s`;
        card.onclick = () => selectFood(card, food.id);
        
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `Select ${food.name}: ${food.desc}`);
        
        const imageContent = food.image
            ? `<img src="${food.image}" alt="${food.name}" style="width: 100%; height: 100%; object-fit: cover;">`
            : `<div style="width: 100%; height: 100%; background: linear-gradient(45deg, var(--accent-light), var(--accent)); display: flex; align-items: center; justify-content: center; font-size: 24px; color: white;">${food.name.charAt(0)}</div>`;
        
        card.innerHTML = `
            <div class="food-image">${imageContent}</div>
            <div class="food-info">
                <div class="food-name">${food.name}</div>
            </div>
            <div class="selection-indicator">✓</div>
        `;
        
        card.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectFood(card, food.id);
            }
        });
        
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'translateY(0)';
            }
        });
        
        foodGrid.appendChild(card);
        
        setTimeout(() => {
            card.classList.add('animate-in');
        }, index * 100);
    });
}

function selectFood(card, foodId) {
    document.querySelectorAll('.food-card').forEach(c => {
        c.classList.remove('selected');
        c.style.transform = 'translateY(0)';
    });
    
    console.log('Selected Restaurant ID:', foodId);  
    
    card.classList.add('selected');
    card.style.transform = 'translateY(-5px)';
    selectedFood = foodId;
    
    card.classList.add('pulse');
    setTimeout(() => card.classList.remove('pulse'), 600);
    
    loadRestaurant(foodId);
    
    const foodName = currentFoodData.find(f => f.id === foodId)?.name;
    showToast(`Selected ${foodName}`);
}

function nextFoods() {
    if (currentFoodPage < totalFoodPages - 1 && !isLoading) {
        loadFoodOptions(currentFoodPage + 1);
        selectedFood = null;
        hideRestaurant();
        
        const nextBtn = document.getElementById('nextBtn');
        if (nextBtn) {
            nextBtn.classList.add('clicked');
            setTimeout(() => nextBtn.classList.remove('clicked'), 200);
        }
    }
}

function previousFoods() {
    if (currentFoodPage > 0 && !isLoading) {
        loadFoodOptions(currentFoodPage - 1);
        selectedFood = null;
        hideRestaurant();
        
        const prevBtn = document.getElementById('prevBtn');
        if (prevBtn) {
            prevBtn.classList.add('clicked');
            setTimeout(() => prevBtn.classList.remove('clicked'), 200);
        }
    }
}

function updateNavigationButtons(hasPrev, hasNext) {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    
    if (prevBtn) {
        prevBtn.disabled = !hasPrev;
        prevBtn.style.opacity = hasPrev ? '1' : '0.5';
        prevBtn.style.cursor = hasPrev ? 'pointer' : 'not-allowed';
        prevBtn.style.pointerEvents = hasPrev ? 'auto' : 'none';
    }
    
    if (nextBtn) {
        nextBtn.disabled = !hasNext;
        nextBtn.style.opacity = hasNext ? '1' : '0.5';
        nextBtn.style.cursor = hasNext ? 'pointer' : 'not-allowed';
        nextBtn.style.pointerEvents = hasNext ? 'auto' : 'none';
    }
}

function updatePageIndicator() {
    const indicator = document.getElementById('pageIndicator');
    if (indicator) {
        indicator.textContent = `${currentFoodPage + 1} of ${totalFoodPages}`;
    }
}

function callRestaurant(phone) {
    window.location.href = `tel:${phone}`;
}

function visitWebsite(website) {
    window.open(website, '_blank', 'noopener,noreferrer');
}

function getDirections(lat, lng) {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
    window.open(url, '_blank', 'noopener,noreferrer');
}

function loadRestaurant(foodId) {
    if (isLoading) return;
    
    isLoading = true;
    const loading = document.getElementById('loading');
    const restaurant = document.getElementById('restaurantSection');
    const sessionId = sessionStorage.getItem('sessionId');
    
    loading.classList.add('show');
    restaurant.classList.remove('show');
    hideError();

    const locationPromise = userLocation ? 
        fetch('/api/update-location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({
                lat: userLocation.latitude,
                lng: userLocation.longitude
            })
        }) : Promise.resolve();

    locationPromise
        .then(() => {
            const params = new URLSearchParams({
                food_id: foodId,
                session_id: sessionId
            });
            
            return fetch(`/api/restaurants?${params.toString()}`, {
                headers: {
                    'X-Session-ID': sessionId,
                    'Content-Type': 'application/json'
                }
            });
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.restaurant) {
                displayRestaurant(data.restaurant);
            } else {
                throw new Error(data.error || 'No restaurants found matching your criteria.');
            }
        })
        .catch(error => {
            console.error('Error loading restaurant:', error);
            showError('Failed to load restaurant recommendations. Please try again.');
        })
        .finally(() => {
            isLoading = false;
            loading.classList.remove('show');
        });
}

function updateActionButtons(restaurant) {
    const actionsContainer = document.getElementById('restaurantActions');
    if (!actionsContainer) return;
    
    let actionsHTML = '';
    
    if (restaurant.phone) {
        actionsHTML += `<button onclick="callRestaurant('${restaurant.phone}')" class="action-btn call-btn">📞 Call</button>`;
    }
    
    if (restaurant.website) {
        actionsHTML += `<button onclick="visitWebsite('${restaurant.website}')" class="action-btn web-btn">🌐 Website</button>`;
    }
    
    if (restaurant.latitude && restaurant.longitude) {
        actionsHTML += `<button onclick="getDirections(${restaurant.latitude}, ${restaurant.longitude})" class="action-btn directions-btn">🗺️ Directions</button>`;
    }
    
    actionsContainer.innerHTML = actionsHTML;
}

function hideRestaurant() {
    const restaurant = document.getElementById('restaurantSection');
    restaurant.classList.remove('show');
}

function getPriceDescription(priceRange) {
    const descriptions = {
        1: 'Budget friendly',
        2: 'Moderate pricing',
        3: 'Upscale dining',
        4: 'Fine dining'
    };
    return descriptions[priceRange] || 'Moderate pricing';
}

function getRestaurantEmoji(tags, properties) {
    const tagEmojiMap = {
        'urn:tag:category:bar': '🍺',
        'urn:tag:category:night_club': '🎵',
        'urn:tag:genre:restaurant:bar': '🍻',
        'urn:tag:genre:restaurant:fast_food': '🍔',
        'urn:tag:genre:restaurant:pizza': '🍕',
        'urn:tag:genre:restaurant:italian': '🍝',
        'urn:tag:genre:restaurant:chinese': '🥡',
        'urn:tag:genre:restaurant:japanese': '🍣',
        'urn:tag:genre:restaurant:mexican': '🌮',
        'urn:tag:genre:restaurant:indian': '🍛',
        'urn:tag:genre:restaurant:thai': '🍜',
        'urn:tag:genre:restaurant:american': '🍔',
        'urn:tag:genre:restaurant:seafood': '🦞',
        'urn:tag:genre:restaurant:steakhouse': '🥩',
        'urn:tag:genre:restaurant:cafe': '☕',
        'urn:tag:category:coffee_shop': '☕',
        'urn:tag:category:bakery': '🧁',
        'urn:tag:category:ice_cream_shop': '🍦'
    };
    
    for (const tag of tags) {
        if (tagEmojiMap[tag.tag_id]) {
            return tagEmojiMap[tag.tag_id];
        }
    }
    
    if (properties.good_for && properties.good_for.length > 0) {
        const goodFor = properties.good_for[0].id;
        if (tagEmojiMap[goodFor]) {
            return tagEmojiMap[goodFor];
        }
    }
    
    return '🏪';
}

function createRestaurantDescription(goodFor, tags) {
    let description = '';
    
    if (goodFor && goodFor.length > 0) {
        const primaryType = goodFor[0].name;
        description = `A popular ${primaryType.toLowerCase()} `;
    } else {
        description = 'A great restaurant ';
    }
    
    const features = [];
    const featureTags = tags.filter(tag => 
        tag.type === 'urn:tag:offerings' || 
        tag.type === 'urn:tag:service_options' ||
        tag.type === 'urn:tag:dining_options'
    );
    
    featureTags.slice(0, 3).forEach(tag => {
        features.push(tag.name.toLowerCase());
    });
    
    if (features.length > 0) {
        description += `offering ${features.join(', ')}.`;
    } else {
        description += 'with great food and atmosphere.';
    }
    
    return description;
}

function showError(message) {
    const errorSection = document.getElementById('errorSection');
    const errorText = document.getElementById('errorText');
    const loading = document.getElementById('loading');
    const restaurant = document.getElementById('restaurantSection');
    
    if (!errorSection || !errorText) {
        showToast(message);
        return;
    }
    
    errorText.textContent = message;
    errorSection.style.display = 'block';
    errorSection.classList.add('show');
    
    loading.classList.remove('show');
    restaurant.classList.remove('show');
    
    setTimeout(hideError, 8000);
}

function hideError() {
    const errorSection = document.getElementById('errorSection');
    if (errorSection) {
        errorSection.classList.remove('show');
        setTimeout(() => {
            errorSection.style.display = 'none';
        }, 300);
    }
}

function retryLastAction() {
    hideError();
    
    if (selectedFood) {
        loadRestaurant(selectedFood);
    } else {
        loadFoodOptions(currentFoodPage);
    }
}

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function addLoadingSpinner(element) {
    const spinner = document.createElement('span');
    spinner.className = 'loading-spinner';
    spinner.innerHTML = '⌛';
    element.appendChild(spinner);
}

function removeLoadingSpinner(element) {
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

function setupAnimations() {
    const observerOptions = {
        root: null,
        rootMargin: '50px',
        threshold: 0.1
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                
                const siblings = Array.from(entry.target.parentNode.children);
                const index = siblings.indexOf(entry.target);
                entry.target.style.animationDelay = `${index * 0.1}s`;
            }
        });
    }, observerOptions);
    
    const animateElements = document.querySelectorAll('.food-card, .restaurant-section, .filter-section');
    animateElements.forEach(el => observer.observe(el));
}

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch(e.key) {
            case 'ArrowLeft':
                if (!document.getElementById('prevBtn').disabled) {
                    e.preventDefault();
                    previousFoods();
                }
                break;
            case 'ArrowRight':
                if (!document.getElementById('nextBtn').disabled) {
                    e.preventDefault();
                    nextFoods();
                }
                break;
            case 'r':
            case 'R':
                if (e.ctrlKey || e.metaKey) return; 
                e.preventDefault();
                retryLastAction();
                break;
            case 'Escape':
                hideError();
                dismissLocationPrompt();
                break;
        }
    });
}

// Analytics tracking
function trackRestaurantView(restaurant) {
    const sessionId = sessionStorage.getItem('sessionId');
    
    fetch('/api/analytics/restaurant-view', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId
        },
        body: JSON.stringify({
            restaurant_id: restaurant.id,
            food_id: selectedFood,
            timestamp: new Date().toISOString(),
            location: userLocation
        })
    }).catch(error => {
        console.log('Analytics tracking failed:', error);
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

function measurePerformance(name, fn) {
    const start = performance.now();
    const result = fn();
    const end = performance.now();
    console.log(`${name} took ${end - start} milliseconds`);
    return result;
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(error) {
                console.log('ServiceWorker registration failed: ', error);
            });
    });
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        debounce,
        throttle,
        calculateDistance: function(lat1, lon1, lat2, lon2) {
            const R = 3959; 
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                    Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }
    };
};

function formatHours(hoursObj) {
    if (!hoursObj) return 'Hours not available';
    
    const today = new Date().toLocaleDateString('en-US', { weekday: 'long' });
    const todayHours = hoursObj[today];
    
    if (!todayHours || todayHours.length === 0) {
        return 'Hours not available';
    }
    
    const todaySchedule = todayHours[0];
    
    if (todaySchedule.closed) {
        return 'Closed today';
    }
    
    if (todaySchedule.opens && todaySchedule.closes) {
        const opens = formatTime(todaySchedule.opens);
        const closes = formatTime(todaySchedule.closes);
        return `Open today: ${opens} - ${closes}`;
    }
    
    return 'Hours not available';
}

function formatTime(timeString) {
    const time = timeString.replace('T', '');
    const [hours, minutes] = time.split(':');
    const hour24 = parseInt(hours);
    const hour12 = hour24 === 0 ? 12 : hour24 > 12 ? hour24 - 12 : hour24;
    const ampm = hour24 >= 12 ? 'PM' : 'AM';
    return `${hour12}:${minutes} ${ampm}`;
}

function displayRestaurantFeatures(tags) {
    const featuresContainer = document.getElementById('restaurantFeatures');
    if (!featuresContainer) return;
    
    const importantFeatures = tags.filter(tag => {
        return tag.type === 'urn:tag:accessibility' ||
               tag.type === 'urn:tag:service_options' ||
               tag.type === 'urn:tag:payments' ||
               tag.type === 'urn:tag:amenity' ||
               tag.type === 'urn:tag:inclusivity';
    });
    
    const displayFeatures = importantFeatures.slice(0, 6);
    
    let featuresHTML = '';
    displayFeatures.forEach(feature => {
        const icon = getFeatureIcon(feature.tag_id);
        featuresHTML += `
            <span class="feature-tag">
                ${icon} ${feature.name}
            </span>
        `;
    });
    
    featuresContainer.innerHTML = featuresHTML;
}

function getFeatureIcon(tagId) {
    const iconMap = {
        'urn:tag:accessibility:wheelchair_accessible_entrance': '♿',
        'urn:tag:accessibility:wheelchair_accessible_seating': '♿',
        'urn:tag:accessibility:wheelchair_accessible_restroom': '♿',
        'urn:tag:service_options:delivery': '🚚',
        'urn:tag:service_options:outdoor_seating': '🌤️',
        'urn:tag:service_options:dine_in': '🍽️',
        'urn:tag:payments:credit_cards': '💳',
        'urn:tag:payments:nfc_mobile_payments': '📱',
        'urn:tag:amenity:wi_fi': 'ᯤ',
        'urn:tag:amenity:restroom': '🚻',
        'urn:tag:planning:accepts_reservations': '📞',
        'urn:tag:amenity:bar_onsite': '🍷',
        'urn:tag:offerings:vegan_options': '🥬',
        'urn:tag:payments:cash_only': '💵',
        'urn:tag:children:good_for_kids': '🧒'
    };
    
    return iconMap[tagId] || '✓';
}

function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 3959;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Enhanced Error handling
function setupErrorHandling() {
    window.addEventListener('error', function(e) {
        console.error('JavaScript error:', e.error);
        showError('Something went wrong. Please refresh the page and try again.');
    });
    
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Unhandled promise rejection:', e.reason);
        showError('Network error. Please check your internet connection.');
    });
    
    // Handle offline/online status
    window.addEventListener('offline', function() {
        showToast('You are offline. Some features may not work.');
    });
    
    window.addEventListener('online', function() {
        showToast('Back online!');
        retryLastAction();
    });
}

function showError(message) {
    const errorSection = document.getElementById('errorSection');
    const errorText = document.getElementById('errorText');
    const loading = document.getElementById('loading');
    const restaurant = document.getElementById('restaurantSection');
    
    if (!errorSection || !errorText) {
        showToast(message);
        return;
    }
    
    errorText.textContent = message;
    errorSection.style.display = 'block';
    errorSection.classList.add('show');
    
    loading.classList.remove('show');
    restaurant.classList.remove('show');
    
    setTimeout(hideError, 8000);
}

function hideError() {
    const errorSection = document.getElementById('errorSection');
    if (errorSection) {
        errorSection.classList.remove('show');
        setTimeout(() => {
            errorSection.style.display = 'none';
        }, 300);
    }
}

function retryLastAction() {
    hideError();
    
    if (selectedFood) {
        loadRestaurant(selectedFood);
    } else {
        loadFoodOptions(currentFoodPage);
    }
}



function addLoadingSpinner(element) {
    const spinner = document.createElement('span');
    spinner.className = 'loading-spinner';
    spinner.innerHTML = '⌛';
    element.appendChild(spinner);
}

function removeLoadingSpinner(element) {
    const spinner = element.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

// Animation setup
function setupAnimations() {
    const observerOptions = {
        root: null,
        rootMargin: '50px',
        threshold: 0.1
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                
                // Stagger animation for multiple elements
                const siblings = Array.from(entry.target.parentNode.children);
                const index = siblings.indexOf(entry.target);
                entry.target.style.animationDelay = `${index * 0.1}s`;
            }
        });
    }, observerOptions);
    
    const animateElements = document.querySelectorAll('.food-card, .restaurant-section, .filter-section');
    animateElements.forEach(el => observer.observe(el));
}

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch(e.key) {
            case 'ArrowLeft':
                if (!document.getElementById('prevBtn').disabled) {
                    e.preventDefault();
                    previousFoods();
                }
                break;
            case 'ArrowRight':
                if (!document.getElementById('nextBtn').disabled) {
                    e.preventDefault();
                    nextFoods();
                }
                break;
            case 'r':
            case 'R':
                if (e.ctrlKey || e.metaKey) return; 
                e.preventDefault();
                retryLastAction();
                break;
            case 'Escape':
                hideError();
                dismissLocationPrompt();
                break;
        }
    });
}

// Analytics tracking
function trackRestaurantView(restaurant) {
    const sessionId = sessionStorage.getItem('sessionId');
    
    fetch('/api/analytics/restaurant-view', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId
        },
        body: JSON.stringify({
            restaurant_id: restaurant.id,
            food_id: selectedFood,
            timestamp: new Date().toISOString(),
            location: userLocation
        })
    }).catch(error => {
        console.log('Analytics tracking failed:', error);
    });
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Performance monitoring
function measurePerformance(name, fn) {
    const start = performance.now();
    const result = fn();
    const end = performance.now();
    console.log(`${name} took ${end - start} milliseconds`);
    return result;
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(error) {
                console.log('ServiceWorker registration failed: ', error);
            });
    });
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        debounce,
        throttle,
        calculateDistance: function(lat1, lon1, lat2, lon2) {
            const R = 3959; 
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                    Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }
    };
};

function displayRestaurant(restaurant) {
    const restaurantData = restaurant;
    
    const name = restaurantData.name || 'Restaurant';
    const properties = restaurantData.properties || {};
    const location = restaurantData.location || {};
    const tags = restaurantData.tags || [];
    
    const restaurantEmoji = document.getElementById('restaurantEmoji');
    const restaurantName = document.getElementById('restaurantName');
    const restaurantDescription = document.getElementById('restaurantDescription');
    
    if (restaurantEmoji) restaurantEmoji.textContent = getRestaurantEmoji(tags, properties);
    if (restaurantName) restaurantName.textContent = name;
    
    if (properties.image && properties.image.url) {
        if (restaurantEmoji) {
            restaurantEmoji.innerHTML = `<img src="${properties.image.url}" alt="${name}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 16px;">`;
        }
    }
    
    const description = createRestaurantDescription(properties.good_for, tags);
    if (restaurantDescription) restaurantDescription.textContent = description;
    
    const rating = parseFloat(properties.business_rating) || 4.0;
    const reviewCount = properties.review_count || Math.floor(Math.random() * 500) + 50; 
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    const priceLevel = properties.price_level || 1;
    console.log("price level", priceLevel, properties.price_level);
    
    const stars = '★'.repeat(fullStars) + 
                 (hasHalfStar ? '☆' : '') + 
                 '☆'.repeat(emptyStars);
    
    const restaurantStars = document.getElementById('restaurantStars');
    const restaurantRating = document.getElementById('restaurantRating');
    if (restaurantStars) restaurantStars.textContent = stars;
    if (restaurantRating) restaurantRating.textContent = `${rating.toFixed(1)} (${reviewCount.toLocaleString()} reviews)`;

    const address = properties.address || 'Address not available';
    let distanceText = '';
    
    if (userLocation && location.lat && location.lon) {
        const distance = calculateDistance(
            userLocation.latitude, 
            userLocation.longitude,
            location.lat,
            location.lon
        );
        distanceText = `${distance.toFixed(1)} miles away • `;
    }
    
    const restaurantDistance = document.getElementById('restaurantDistance');
    if (restaurantDistance) restaurantDistance.textContent = distanceText + address;
    
    // const priceRange = extractPriceRange(tags) || '$';
    const priceDesc = getPriceDescription(priceLevel);
    const restaurantPrice = document.getElementById('restaurantPrice');
    if (restaurantPrice) restaurantPrice.textContent = `${priceDesc}`;
    
    const hoursText = formatHours(properties.hours);
    const restaurantHours = document.getElementById('restaurantHours');
    if (restaurantHours) restaurantHours.textContent = hoursText;
    
    const phone = properties.phone || 'Phone not available';
    const restaurantPhone = document.getElementById('restaurantPhone');
    if (restaurantPhone) restaurantPhone.textContent = phone;
    
    displayRestaurantFeatures(tags);
    
    updateActionButtons({
        phone: properties.phone,
        website: properties.website,
        latitude: location.lat,
        longitude: location.lon,
        name: name
    });
    
    const restaurantSection = document.getElementById('restaurantSection');
    restaurantSection.classList.add('show');
    
    setTimeout(() => {
        const offset = window.innerWidth < 768 ? 100 : 50;
        const elementPosition = restaurantSection.offsetTop - offset;
        window.scrollTo({
            top: elementPosition,
            behavior: 'smooth'
        });
    }, 300);
    
    trackRestaurantView({
        id: restaurantData.entity_id,
        name: name,
        ...restaurantData
    });
}