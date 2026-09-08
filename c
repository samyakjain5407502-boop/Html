import os

filepath = os.path.join('jainzee-website', 'templates', 'index.html')
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Task 2: Fix modal quantity input color (white text on white bg -> dark)
old_modal_qty = 'background: white; color: var(--text); font-size: 1rem; text-align: center;'
new_modal_qty = 'background: white; color: #121212; font-size: 1rem; text-align: center;'
content = content.replace(old_modal_qty, new_modal_qty)

# Task 4: Move video into hero section
# Replace the hero section to include the video element
old_hero = '''    <!-- ===== HERO SECTION ===== -->
    <section class="hero" id="home">
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <img id="heroLogo" src="{{ url_for('static', filename='images/logo.svg') }}" alt="Jainzee Logo" class="hero-logo" style="display: inline-block !important; visibility: visible !important; opacity: 1 !important;">
            <h1 id="heroShopName">Jainzee Food Processing Industries</h1>
            <p id="heroTagline">Pure & Premium Dry Fruits</p>
            <div class="hero-buttons">
                <a href="#products" class="btn btn-primary" data-i18n="explore_products">Explore Products</a>
                <a href="#contact" class="btn btn-outline" data-i18n="contact_us">Contact Us</a>
            </div>
        </div>
    </section>

    <!-- ===== MAIN PAGE VIDEO BANNER ===== -->
    <section class="video-banner-section" id="videoBanner">
        <div class="container">
            <div class="main-product-video-wrapper">
                <div class="video-banner-card" id="videoBannerCard" style="display:none;">
                    <div class="video-banner-icon">
                        <i class="fas fa-video"></i>
                    </div>
                    <video id="mainBannerVideo" controls preload="metadata" playsinline>
                        <source src="" type="video/mp4" id="mainBannerVideoSource">
                        Your browser does not support video playback.
                    </video>
                </div>
            </div>
        </div>
    </section>'''

new_hero = '''    <!-- ===== HERO SECTION ===== -->
    <section class="hero" id="home">
        <div class="hero-overlay"></div>
        <div class="hero-video-container" id="heroVideoContainer">
            <div class="hero-video-wrapper" id="heroVideoWrapper">
                <div class="hero-video-overlay" id="heroVideoOverlay"></div>
                <video id="mainBannerVideo" controls preload="metadata" playsinline muted loop>
                    <source src="" type="video/mp4" id="mainBannerVideoSource">
                    Your browser does not support video playback.
                </video>
                <div class="video-play-icon" id="videoPlayIcon" style="display: none;">
                    <i class="fas fa-play"></i>
                </div>
            </div>
        </div>
        <div class="hero-content">
            <img id="heroLogo" src="{{ url_for('static', filename='images/logo.svg') }}" alt="Jainzee Logo" class="hero-logo" style="display: inline-block !important; visibility: visible !important; opacity: 1 !important;">
            <h1 id="heroShopName">Jainzee Food Processing Industries</h1>
            <p id="heroTagline">Pure & Premium Dry Fruits</p>
            <div class="hero-buttons">
                <a href="#products" class="btn btn-primary" data-i18n="explore_products">Explore Products</a>
                <a href="#contact" class="btn btn-outline" data-i18n="contact_us">Contact Us</a>
            </div>
        </div>
    </section>'''

content = content.replace(old_hero, new_hero)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
print('index.html - Contains >>>>>>>:', '>>>>>>>' in content)
print('index.html - Has dark modal qty:', 'color: #121212; font-size: 1rem; text-align: center;' in content)
print('index.html - Has hero video container:', 'hero-video-container' in content)
print('index.html - Has hero video wrapper:', 'hero-video-wrapper' in content)
print('index.html - Video moved to hero:', 'hero-video-container' in content and 'video-banner-section' not in content)
