let currentFoodSet = 0;
let selectedFood = null;

const foodSets = [
    [
        { emoji: '🍝', name: ' Pasta', desc: 'desc', id: 'pasta' },
        { emoji: '🥗', name: ' Salad', desc: 'desc', id: 'salad' },
        { emoji: '🍔', name: ' Burger', desc: 'descs', id: 'burger' },
        { emoji: '🍕', name: ' Pizza', desc: 'desc', id: 'pizza' }
    ],
    [
        { emoji: '🍜', name: ' Bowl', desc: 'desc', id: 'ramen' },
        { emoji: '🌮', name: ' Tacos', desc: 'desc', id: 'tacos' },
        { emoji: '🥙', name: ' Wrap', desc: 'desc', id: 'wrap' },
        { emoji: '🍛', name: ' Bowl', desc: 'desc', id: 'curry' }
    ],
    [
        { emoji: '🥞', name: ' Pancakes', desc: 'desc', id: 'pancakes' },
        { emoji: '🍳', name: ' Bowl', desc: 'desc', id: 'breakfast' },
        { emoji: '🥐', name: ' Toast', desc: 'desc', id: 'toast' },
        { emoji: '🧇', name: ' Waffle', desc: 'desc', id: 'waffle' }
    ]
];

function renderFoodCards() {
    const foodGrid = document.getElementById('foodGrid');
    const currentFoods = foodSets[currentFoodSet];
    
    foodGrid.innerHTML = '';
    
    currentFoods.forEach(food => {
        const card = document.createElement('div');
        card.className = 'food-card';
        card.dataset.food = food.id;
        card.onclick = () => selectFood(card, food.id);
        
        card.innerHTML = `
            <div class="food-image">${food.emoji}</div>
            <div class="food-info">
                <div class="food-name">${food.name}</div>
                <div class="food-description">${food.desc}</div>
            </div>
            <div class="selection-indicator">✓</div>
        `;
        
        foodGrid.appendChild(card);
    });
    
    updateNavigationButtons();
}

function selectFood(card, foodId) {
    // Remove previous selection
    document.querySelectorAll('.food-card').forEach(c => c.classList.remove('selected'));
    
    // Add selection to clicked card
    card.classList.add('selected');
    selectedFood = foodId;
    
    // Show loading and then restaurant
    showRestaurant();
}

function showRestaurant() {
    const loading = document.getElementById('loading');
    const restaurant = document.getElementById('restaurantSection');
    
    // Show loading
    loading.classList.add('show');
    restaurant.classList.remove('show');
    
    // Simulate API call delay
    setTimeout(() => {
        loading.classList.remove('show');
        restaurant.classList.add('show');
        restaurant.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 1500);
}

function nextFoods() {
    if (currentFoodSet < foodSets.length - 1) {
        currentFoodSet++;
        renderFoodCards();
        selectedFood = null;
        document.getElementById('restaurantSection').classList.remove('show');
    }
}

function previousFoods() {
    if (currentFoodSet > 0) {
        currentFoodSet--;
        renderFoodCards();
        selectedFood = null;
        document.getElementById('restaurantSection').classList.remove('show');
    }
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    
    prevBtn.disabled = currentFoodSet === 0;
    nextBtn.disabled = currentFoodSet === foodSets.length - 1;
}

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    renderFoodCards();
    
    // Add filter change listeners
    document.querySelectorAll('.filter-input').forEach(input => {
        input.addEventListener('change', function() {
            console.log('Filter changed:', this.id, this.checked);
        });
    });
});

// Add smooth scrolling behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});