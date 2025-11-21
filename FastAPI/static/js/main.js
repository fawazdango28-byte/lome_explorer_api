// ============================================
// FICHIER: FastAPI/static/js/main.js
// JavaScript personnalisé pour l'application
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ==========================================
    // Animation des cartes au survol
    // ==========================================
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'transform 0.3s ease';
        });
    });

    // ==========================================
    // Confirmation de suppression
    // ==========================================
    const deleteButtons = document.querySelectorAll('[data-action="delete"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Êtes-vous sûr de vouloir supprimer cet élément ?')) {
                e.preventDefault();
                return false;
            }
        });
    });

    // ==========================================
    // Auto-hide des messages flash
    // ==========================================
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // Ferme après 5 secondes
    });

    // ==========================================
    // Recherche en temps réel
    // ==========================================
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                // La recherche se fait via le formulaire
                console.log('Recherche:', this.value);
            }, 500);
        });
    }

    // ==========================================
    // Validation des formulaires
    // ==========================================
    const forms = document.querySelectorAll('form.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // ==========================================
    // Gestion des étoiles pour les avis
    // ==========================================
    const starRatings = document.querySelectorAll('.star-rating');
    starRatings.forEach(rating => {
        const stars = rating.querySelectorAll('.star');
        const input = rating.querySelector('input[name="note"]');
        
        stars.forEach((star, index) => {
            star.addEventListener('click', function() {
                const value = index + 1;
                if (input) input.value = value;
                
                // Mettre à jour l'affichage
                stars.forEach((s, i) => {
                    if (i < value) {
                        s.classList.remove('far');
                        s.classList.add('fas');
                    } else {
                        s.classList.remove('fas');
                        s.classList.add('far');
                    }
                });
            });
            
            star.addEventListener('mouseenter', function() {
                const value = index + 1;
                stars.forEach((s, i) => {
                    if (i < value) {
                        s.style.color = '#f39c12';
                    }
                });
            });
        });
        
        rating.addEventListener('mouseleave', function() {
            const currentValue = input ? parseInt(input.value) || 0 : 0;
            stars.forEach((s, i) => {
                s.style.color = i < currentValue ? '#f39c12' : '#ddd';
            });
        });
    });

    // ==========================================
    // Scroll to top button
    // ==========================================
    const scrollBtn = createScrollButton();
    document.body.appendChild(scrollBtn);

    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            scrollBtn.style.display = 'block';
        } else {
            scrollBtn.style.display = 'none';
        }
    });

    scrollBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // ==========================================
    // Chargement dynamique de contenu
    // ==========================================
    const loadMoreButtons = document.querySelectorAll('.load-more');
    loadMoreButtons.forEach(button => {
        button.addEventListener('click', function() {
            const nextPage = this.dataset.nextPage;
            if (nextPage) {
                loadMoreContent(nextPage, this);
            }
        });
    });

    // ==========================================
    // Géolocalisation du navigateur
    // ==========================================
    const geolocateBtn = document.getElementById('geolocate-btn');
    if (geolocateBtn) {
        geolocateBtn.addEventListener('click', function() {
            if (navigator.geolocation) {
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Localisation...';
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        document.getElementById('latitude').value = position.coords.latitude;
                        document.getElementById('longitude').value = position.coords.longitude;
                        this.innerHTML = '<i class="fas fa-check"></i> Localisé';
                        this.classList.remove('btn-primary');
                        this.classList.add('btn-success');
                    },
                    (error) => {
                        alert('Erreur de géolocalisation: ' + error.message);
                        this.innerHTML = '<i class="fas fa-times"></i> Erreur';
                        this.classList.remove('btn-primary');
                        this.classList.add('btn-danger');
                    }
                );
            } else {
                alert('La géolocalisation n\'est pas supportée par votre navigateur');
            }
        });
    }

    // ==========================================
    // Partage sur les réseaux sociaux
    // ==========================================
    const shareButtons = document.querySelectorAll('.btn-share');
    shareButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const url = window.location.href;
            const title = document.title;
            
            if (navigator.share) {
                navigator.share({
                    title: title,
                    url: url
                }).catch(err => console.log('Erreur de partage:', err));
            } else {
                // Fallback: copier l'URL
                navigator.clipboard.writeText(url).then(() => {
                    alert('Lien copié dans le presse-papier !');
                });
            }
        });
    });

    // ==========================================
    // Tooltips Bootstrap
    // ==========================================
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // ==========================================
    // Popovers Bootstrap
    // ==========================================
    const popoverTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="popover"]')
    );
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// ==========================================
// Fonctions utilitaires
// ==========================================

function createScrollButton() {
    const btn = document.createElement('button');
    btn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    btn.className = 'btn btn-primary rounded-circle';
    btn.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 1000;
        display: none;
        width: 50px;
        height: 50px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    `;
    return btn;
}

function loadMoreContent(url, button) {
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Chargement...';
    button.disabled = true;
    
    fetch(url)
        .then(response => response.text())
        .then(html => {
            // Traiter le contenu chargé
            console.log('Contenu chargé');
            button.innerHTML = 'Charger plus';
            button.disabled = false;
        })
        .catch(error => {
            console.error('Erreur:', error);
            button.innerHTML = 'Erreur de chargement';
            button.classList.add('btn-danger');
        });
}

// ==========================================
// Fonction pour formater les dates
// ==========================================
function formatDate(date) {
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(date).toLocaleDateString('fr-FR', options);
}

// ==========================================
// Fonction pour calculer la distance
// ==========================================
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Rayon de la Terre en km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const distance = R * c;
    return distance.toFixed(2);
}

// ==========================================
// WebSocket pour les notifications en temps réel
// ==========================================
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/events/`;
    
    try {
        const socket = new WebSocket(wsUrl);
        
        socket.onopen = function() {
            console.log('WebSocket connecté');
        };
        
        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        socket.onerror = function(error) {
            console.error('Erreur WebSocket:', error);
        };
        
        socket.onclose = function() {
            console.log('WebSocket déconnecté');
            // Reconnexion après 5 secondes
            setTimeout(initWebSocket, 5000);
        };
        
        return socket;
    } catch (error) {
        console.error('Impossible de créer le WebSocket:', error);
    }
}

function handleWebSocketMessage(data) {
    if (data.type === 'new_event') {
        showNotification('Nouvel événement', data.message);
    } else if (data.type === 'event_updated') {
        showNotification('Événement mis à jour', data.message);
    }
}

function showNotification(title, message) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: message,
            icon: '/static/images/logo.png'
        });
    } else {
        // Afficher une notification dans la page
        const alert = document.createElement('div');
        alert.className = 'alert alert-info alert-dismissible fade show';
        alert.innerHTML = `
            <strong>${title}</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container').prepend(alert);
        setTimeout(() => alert.remove(), 5000);
    }
}

// Demander la permission pour les notifications
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

// Initialiser le WebSocket si on est sur une page appropriée
if (window.location.pathname !== '/login/' && window.location.pathname !== '/register/') {
    // initWebSocket(); // Décommenter pour activer les WebSockets
}