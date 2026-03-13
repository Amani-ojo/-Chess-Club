/* ============================================================
   ESCHEN CHESS CLUB — Custom JavaScript
   ============================================================
   This file contains client-side interactivity for the site.
   ============================================================ */


// ==================== NAVBAR SCROLL EFFECT ====================
// Changes the navbar background opacity when the user scrolls down
window.addEventListener('scroll', function() {
    var navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.style.backgroundColor = 'rgba(26, 26, 46, 0.95)';
        navbar.style.backdropFilter = 'blur(10px)';
    } else {
        navbar.style.backgroundColor = '#1a1a2e';
        navbar.style.backdropFilter = 'none';
    }
});


// ==================== ANIMATE ON SCROLL ====================
// Adds a fade-in animation to cards when they scroll into view
document.addEventListener('DOMContentLoaded', function() {
    var cards = document.querySelectorAll('.player-card, .match-card, .match-card-full, .announcement-card, .about-card');

    var observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });

    cards.forEach(function(card) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
});


// ==================== AUTO-DISMISS ALERTS ====================
// Automatically closes Bootstrap alert messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});
