"""
Seed data: 10 system design challenges based on real FAANG interview topics.
"""

from sqlalchemy.orm import Session
from app.models.challenge import Challenge


SEED_CHALLENGES = [
    {
        "title": "Design WhatsApp",
        "slug": "design-whatsapp",
        "difficulty": "hard",
        "category": "messaging",
        "icon": "message-circle",
        "estimated_time": 60,
        "tags": ["messaging", "real-time", "encryption", "distributed"],
        "description": "Design a messaging platform like WhatsApp that supports one-to-one and group messaging with real-time delivery, read receipts, and end-to-end encryption.",
        "requirements": "Support 2 billion users with millions of messages per second. Messages must be delivered in order and reliably.",
        "functional_requirements": "1. One-to-one messaging\n2. Group messaging (up to 256 members)\n3. Read receipts and delivery status\n4. Media sharing (images, videos, documents)\n5. End-to-end encryption\n6. User online/offline status\n7. Message history sync across devices",
        "non_functional_requirements": "1. Low latency (<200ms message delivery)\n2. High availability (99.99%)\n3. Message ordering guarantees\n4. Data encryption at rest and in transit\n5. Support for 2B+ users",
        "expected_scale": "2 billion users, 100 billion messages per day, 65 billion media shared daily",
        "constraints": "Messages must be encrypted end-to-end. System must work on low bandwidth connections.",
    },
    {
        "title": "Design Instagram",
        "slug": "design-instagram",
        "difficulty": "hard",
        "category": "social-media",
        "icon": "camera",
        "estimated_time": 60,
        "tags": ["social-media", "feeds", "media", "recommendation"],
        "description": "Design a photo and video sharing social network like Instagram with feeds, stories, reels, and real-time notifications.",
        "requirements": "Support 1 billion monthly active users. Generate personalized news feeds and support high media throughput.",
        "functional_requirements": "1. User registration and profiles\n2. Photo and video uploads\n3. News feed generation\n4. Like, comment, and share\n5. Stories (24-hour expiry)\n6. Follow/unfollow users\n7. Explore and search\n8. Direct messaging",
        "non_functional_requirements": "1. High availability (99.9%)\n2. Feed generation <500ms\n3. Media storage optimization\n4. CDN for global distribution\n5. Eventual consistency acceptable for feeds",
        "expected_scale": "1 billion MAU, 500 million daily stories, 100 million photos uploaded daily",
        "constraints": "Feed must be personalized. Media must be served globally with low latency.",
    },
    {
        "title": "Design Uber",
        "slug": "design-uber",
        "difficulty": "hard",
        "category": "ride-sharing",
        "icon": "car",
        "estimated_time": 60,
        "tags": ["ride-sharing", "geolocation", "matching", "real-time"],
        "description": "Design a ride-sharing platform like Uber with real-time driver matching, trip tracking, surge pricing, and payment processing.",
        "requirements": "Match riders with nearby drivers in real-time. Support millions of concurrent rides with live GPS tracking.",
        "functional_requirements": "1. Rider can request a ride\n2. Match rider with nearest available driver\n3. Real-time location tracking\n4. Trip fare estimation and calculation\n5. Payment processing\n6. Rating system for riders and drivers\n7. Surge pricing during high demand\n8. Trip history",
        "non_functional_requirements": "1. Low latency matching (<30 seconds)\n2. Real-time GPS updates\n3. High availability\n4. Accurate fare calculation\n5. Fraud detection",
        "expected_scale": "20 million daily rides, 5 million drivers, location updates every 4 seconds",
        "constraints": "Location matching must be efficient. System must handle geographic partitioning.",
    },
    {
        "title": "Design Netflix",
        "slug": "design-netflix",
        "difficulty": "medium",
        "category": "streaming",
        "icon": "play",
        "estimated_time": 45,
        "tags": ["streaming", "cdn", "recommendation", "video"],
        "description": "Design a video streaming platform like Netflix with content delivery, recommendation engine, and adaptive bitrate streaming.",
        "requirements": "Stream video content to 200+ million subscribers globally with minimal buffering.",
        "functional_requirements": "1. User registration and profiles\n2. Content catalog browsing\n3. Video streaming with adaptive bitrate\n4. Personalized recommendations\n5. Watch history and continue watching\n6. Multiple device support\n7. Download for offline viewing\n8. Parental controls",
        "non_functional_requirements": "1. <2 second video start time\n2. 99.99% availability\n3. Global CDN distribution\n4. Adaptive quality based on bandwidth\n5. Support 4K/HDR streaming",
        "expected_scale": "200 million subscribers, 15,000+ titles, 1 billion hours watched per week",
        "constraints": "Must support various devices and bandwidths. Content must be DRM protected.",
    },
    {
        "title": "Design Amazon E-Commerce",
        "slug": "design-amazon",
        "difficulty": "hard",
        "category": "e-commerce",
        "icon": "shopping-cart",
        "estimated_time": 60,
        "tags": ["e-commerce", "inventory", "payment", "search"],
        "description": "Design an e-commerce platform like Amazon with product catalog, search, cart, checkout, payments, and order management.",
        "requirements": "Handle millions of products, high traffic during sales events, and reliable order processing.",
        "functional_requirements": "1. Product catalog with categories\n2. Full-text search with filters\n3. Shopping cart\n4. Checkout and payment\n5. Order tracking\n6. Product reviews and ratings\n7. Seller management\n8. Inventory management\n9. Recommendation engine",
        "non_functional_requirements": "1. Handle 100K+ orders per second during peak\n2. Search results <200ms\n3. Zero data loss for orders\n4. Strong consistency for inventory\n5. Global availability",
        "expected_scale": "350 million products, 300 million users, peak 100K orders/second",
        "constraints": "Inventory must be accurate to prevent overselling. Payment processing must be reliable.",
    },
    {
        "title": "Design YouTube",
        "slug": "design-youtube",
        "difficulty": "medium",
        "category": "streaming",
        "icon": "video",
        "estimated_time": 50,
        "tags": ["video", "upload", "streaming", "cdn"],
        "description": "Design a video sharing platform like YouTube with upload, transcoding, streaming, search, and recommendation capabilities.",
        "requirements": "Support 500 hours of video uploaded per minute and 1 billion hours watched per day.",
        "functional_requirements": "1. Video upload and transcoding\n2. Video streaming\n3. Search and discovery\n4. Comments and likes\n5. Subscriptions and notifications\n6. Playlists\n7. Creator analytics\n8. Monetization/ads",
        "non_functional_requirements": "1. Fast video processing pipeline\n2. CDN for global delivery\n3. Support multiple resolutions\n4. Low startup latency\n5. High availability",
        "expected_scale": "2 billion MAU, 500 hours uploaded per minute, 1 billion hours watched daily",
        "constraints": "Video transcoding must be efficient. Support various formats and resolutions.",
    },
    {
        "title": "Design Google Drive",
        "slug": "design-google-drive",
        "difficulty": "medium",
        "category": "storage",
        "icon": "hard-drive",
        "estimated_time": 45,
        "tags": ["storage", "sync", "collaboration", "file-system"],
        "description": "Design a cloud storage service like Google Drive with file upload, sync, sharing, collaboration, and version history.",
        "requirements": "Support billions of files with real-time sync across devices and collaborative editing.",
        "functional_requirements": "1. File upload/download\n2. Real-time sync across devices\n3. File and folder sharing\n4. Collaborative editing\n5. Version history\n6. Search files\n7. Trash and recovery\n8. Access control",
        "non_functional_requirements": "1. Strong consistency for file operations\n2. Data durability (99.999999999%)\n3. Low sync latency\n4. Support large files (5TB)\n5. Conflict resolution",
        "expected_scale": "1 billion users, 15 billion files, 2 trillion storage operations daily",
        "constraints": "File sync must handle conflicts gracefully. Storage must be highly durable.",
    },
    {
        "title": "Design Twitter/X",
        "slug": "design-twitter",
        "difficulty": "medium",
        "category": "social-media",
        "icon": "at-sign",
        "estimated_time": 50,
        "tags": ["social-media", "timeline", "real-time", "trending"],
        "description": "Design a micro-blogging platform like Twitter/X with timelines, trending topics, real-time updates, and content moderation.",
        "requirements": "Support 500 million tweets per day with real-time timeline delivery to followers.",
        "functional_requirements": "1. Post tweets (280 chars + media)\n2. Follow/unfollow users\n3. Home timeline (fan-out)\n4. Like, retweet, reply\n5. Trending topics\n6. Search tweets and users\n7. Notifications\n8. Direct messages",
        "non_functional_requirements": "1. Timeline generation <300ms\n2. Real-time delivery for breaking news\n3. Handle celebrity accounts (100M+ followers)\n4. Eventual consistency for timelines\n5. High availability",
        "expected_scale": "400 million MAU, 500 million tweets/day, celebrity users with 100M+ followers",
        "constraints": "Fan-out on write vs fan-out on read trade-offs. Handle hot partitions for viral tweets.",
    },
    {
        "title": "Design Food Delivery Platform",
        "slug": "design-food-delivery",
        "difficulty": "medium",
        "category": "logistics",
        "icon": "utensils",
        "estimated_time": 45,
        "tags": ["logistics", "geolocation", "ordering", "real-time"],
        "description": "Design a food delivery platform like DoorDash or Swiggy with restaurant management, order processing, delivery tracking, and payment.",
        "requirements": "Match orders with delivery partners, optimize delivery routes, and provide real-time tracking.",
        "functional_requirements": "1. Restaurant catalog and menu\n2. Search and filter restaurants\n3. Place orders with customization\n4. Real-time order tracking\n5. Delivery partner assignment\n6. Payment processing\n7. Rating and reviews\n8. Order history",
        "non_functional_requirements": "1. Order placement <5 seconds\n2. Real-time delivery tracking\n3. Accurate ETA prediction\n4. High availability during peak hours\n5. Handle concurrent orders",
        "expected_scale": "50 million monthly orders, 500K restaurants, 2 million delivery partners",
        "constraints": "Must handle peak hour load (2-3x normal). Delivery assignment must be optimal.",
    },
    {
        "title": "Design Notification System",
        "slug": "design-notification-system",
        "difficulty": "easy",
        "category": "infrastructure",
        "icon": "bell",
        "estimated_time": 35,
        "tags": ["notifications", "push", "email", "sms", "infrastructure"],
        "description": "Design a scalable notification service that supports push notifications, email, SMS, and in-app notifications with user preferences and rate limiting.",
        "requirements": "Send millions of notifications per day across multiple channels with delivery guarantees and user preference management.",
        "functional_requirements": "1. Multi-channel delivery (push, email, SMS, in-app)\n2. User notification preferences\n3. Notification templates\n4. Rate limiting per user\n5. Delivery tracking and analytics\n6. Priority levels\n7. Batch notifications\n8. Notification history",
        "non_functional_requirements": "1. Delivery within seconds for high priority\n2. At-least-once delivery guarantee\n3. Handle millions of notifications/day\n4. Rate limiting to prevent spam\n5. Retry with exponential backoff",
        "expected_scale": "100 million notifications/day, 50 million users, 4 channels",
        "constraints": "Must respect user preferences and rate limits. Must handle provider failures gracefully.",
    },
]


def seed_challenges(db: Session):
    """Insert seed challenges if the database is empty."""
    existing_count = db.query(Challenge).count()
    if existing_count > 0:
        return

    for data in SEED_CHALLENGES:
        challenge = Challenge(**data)
        db.add(challenge)

    db.commit()
    print(f"[SEED] Seeded {len(SEED_CHALLENGES)} challenges")


def seed_admin(db: Session):
    """Create a default admin user if none exists."""
    from app.models.user import User
    from app.core.security import hash_password

    admin = db.query(User).filter(User.role == "admin").first()
    if admin:
        return

    admin = User(
        name="Admin",
        email="admin@codementor.com",
        password_hash=hash_password("admin123"),
        role="admin",
        skill_level="expert",
    )
    db.add(admin)
    db.commit()
    print("[SEED] Created default admin user (admin@codementor.com / admin123)")
