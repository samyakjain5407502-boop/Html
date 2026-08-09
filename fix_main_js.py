import os

filepath = os.path.join('jainzee-website', 'static', 'js', 'main.js')
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Task 2: Fix inline quantity input color (white text on light gray -> dark)
old_qty = 'background: #F8F9FA; color: var(--text); font-size: 0.9rem;" onclick="event.stopPropagation();'
new_qty = 'background: #F8F9FA; color: #121212; font-size: 0.9rem;" onclick="event.stopPropagation();'
content = content.replace(old_qty, new_qty)

# Task 1: Add reviews container to product card
# Find the rating box section and add a reviews container after it
old_rating_box = '''                <!-- Compact Rating Box -->
                <div class="rating-box" style="background: #F8F9FA; border: 1px solid rgba(184,134,11,0.15); border-radius: 10px; padding: 12px; margin-top: 10px; cursor: pointer;" onclick="event.stopPropagation(); openReviewsModal(${p.id})">
                    <div class="rating-display" id="rating-${p.id}" style="margin-bottom: 8px;">
                        <div class="stars">
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                        </div>
                        <span class="rating-text">No reviews</span>
                    </div>
                    <button class="btn btn-outline" style="width: 100%; padding: 6px; font-size: 0.8rem; border: 1px solid var(--primary); color: var(--primary); background: transparent;" onclick="event.stopPropagation(); openReviewsModal(${p.id})">
                        <i class="fas fa-comments"></i> Read Reviews
                    </button>
                </div>'''

new_rating_box = '''                <!-- Compact Rating Box -->
                <div class="rating-box" style="background: #F8F9FA; border: 1px solid rgba(184,134,11,0.15); border-radius: 10px; padding: 12px; margin-top: 10px; cursor: pointer;" onclick="event.stopPropagation(); openReviewsModal(${p.id})">
                    <div class="rating-display" id="rating-${p.id}" style="margin-bottom: 8px;">
                        <div class="stars">
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                            <i class="fas fa-star star-empty"></i>
                        </div>
                        <span class="rating-text">No reviews</span>
                    </div>
                    <button class="btn btn-outline" style="width: 100%; padding: 6px; font-size: 0.8rem; border: 1px solid var(--primary); color: var(--primary); background: transparent;" onclick="event.stopPropagation(); openReviewsModal(${p.id})">
                        <i class="fas fa-comments"></i> Read Reviews
                    </button>
                </div>
                
                <!-- Reviews Container - dynamically populated by loadProductReviews -->
                <div id="reviews-${p.id}" class="review-section" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,215,0,0.1); display: none;">
                    <div class="reviews-list" style="max-height: 200px; overflow-y: auto;"></div>
                </div>'''

content = content.replace(old_rating_box, new_rating_box)

# Task 1: Update loadProductReviews to also show the reviews container
old_load_reviews = '''        // Display reviews list
        if (!data.reviews.length) {
            reviewsContainer.innerHTML = '<p class="no-reviews">No reviews yet. Be the first to review!</p>';
            return;
        }
        
        let html = '<div class="reviews-list">';
        data.reviews.forEach(review => {
            html += `
                <div class="review-item">
                    <div class="review-header">
                        <span class="review-author">${review.customer_name}</span>
                        <span class="review-date">${new Date(review.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="review-rating">${generateStars(review.rating)}</div>
                    ${review.review_text ? `<p class="review-text">${review.review_text}</p>` : ''}
                </div>
            `;
        });
        html += '</div>';
        reviewsContainer.innerHTML = html;'''

new_load_reviews = '''        // Display reviews list
        if (!data.reviews.length) {
            reviewsContainer.innerHTML = '<p class="no-reviews">No reviews yet. Be the first to review!</p>';
            reviewsContainer.style.display = 'block';
            return;
        }
        
        let html = '<div class="reviews-list">';
        data.reviews.forEach(review => {
            html += `
                <div class="review-item">
                    <div class="review-header">
                        <span class="review-author">${review.customer_name}</span>
                        <span class="review-date">${new Date(review.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="review-rating">${generateStars(review.rating)}</div>
                    ${review.review_text ? `<p class="review-text">${review.review_text}</p>` : ''}
                </div>
            `;
        });
        html += '</div>';
        reviewsContainer.innerHTML = html;
        reviewsContainer.style.display = 'block';'''

content = content.replace(old_load_reviews, new_load_reviews)

# Task 1: Update submitReview to reload reviews into the card after submission
old_submit = '''        alert('Review submitted successfully!');
        closeReviewModal();
        
        // Reload reviews
        loadProductReviews(currentReviewProductId);'''

new_submit = '''        alert('Review submitted successfully!');
        closeReviewModal();
        
        // Reload reviews on product card and in modal
        loadProductReviews(currentReviewProductId);
        loadReviewsIntoModal(currentReviewProductId);'''

content = content.replace(old_submit, new_submit)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
print('main.js - Contains >>>>>>>:', '>>>>>>>' in content)
print('main.js - Has reviews container:', 'reviews-${p.id}' in content)
print('main.js - Has dark quantity input:', 'color: #121212' in content)
print('main.js - Has reload reviews in submitReview:', 'loadReviewsIntoModal(currentReviewProductId)' in content)
