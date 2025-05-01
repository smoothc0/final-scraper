// Pricing card hover effects
document.addEventListener('DOMContentLoaded', function() {
    const pricingCards = document.querySelectorAll('.pricing-card');
    
    pricingCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-10px)';
            card.style.boxShadow = '0 15px 30px rgba(0, 0, 0, 0.2)';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
            card.style.boxShadow = '';
        });
    });
    
    // Update progress bar on dashboard
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        const limit = parseInt(progressBar.dataset.limit);
        const scraped = parseInt(progressBar.dataset.scraped);
        const percentage = Math.min((scraped / limit) * 100, 100);
        progressBar.style.width = `${percentage}%`;
    }
    
    // Auto-hide flash messages
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 3000);
    });
});

// Dark/light mode toggle
function toggleDarkMode() {
    const body = document.body;
    body.classList.toggle('light-mode');
    
    // Save preference to localStorage
    const isLight = body.classList.contains('light-mode');
    localStorage.setItem('lightMode', isLight);
}

// Check for saved preference
if (localStorage.getItem('lightMode') === 'true') {
    document.body.classList.add('light-mode');
}