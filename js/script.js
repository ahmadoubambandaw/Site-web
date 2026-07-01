'use strict';

const WHATSAPP_NUMBER = '221781338213';

/* ============================================================
   DONNÉES PRODUITS
   ============================================================ */
const PRODUCTS = [
  { id: 1, name: 'Polo Lacoste Classique', category: 'polos', price: 10000, oldPrice: null, icon: 'icon-polo', badge: 'Best-seller', rating: 5 },
  { id: 2, name: 'Polo Lacoste Piqué', category: 'polos', price: 12000, oldPrice: null, icon: 'icon-polo', badge: 'Nouveau', rating: 5 },
  { id: 3, name: 'Polo Lacoste Manches Longues', category: 'polos', price: 15000, oldPrice: null, icon: 'icon-polo', badge: null, rating: 4 },
  { id: 4, name: 'Chemise Habillée Blanche', category: 'chemises', price: 12000, oldPrice: null, icon: 'icon-shirt', badge: null, rating: 5 },
  { id: 5, name: 'Chemise Slim Imprimée', category: 'chemises', price: 13000, oldPrice: null, icon: 'icon-shirt', badge: 'Nouveau', rating: 4 },
  { id: 6, name: 'Chemise Lin Été', category: 'chemises', price: 11000, oldPrice: 14000, icon: 'icon-shirt', badge: 'Promo', rating: 5 },
  { id: 7, name: 'Ensemble Prêt-à-Porter Chic', category: 'ensembles', price: 25000, oldPrice: null, icon: 'icon-outfit', badge: 'Best-seller', rating: 5 },
  { id: 8, name: 'Ensemble Sport Deux-Pièces', category: 'ensembles', price: 20000, oldPrice: null, icon: 'icon-outfit', badge: null, rating: 4 },
  { id: 9, name: 'Blazer Ville', category: 'ensembles', price: 35000, oldPrice: null, icon: 'icon-outfit', badge: null, rating: 5 },
  { id: 10, name: 'Montre Classique Cuir', category: 'montres', price: 18000, oldPrice: null, icon: 'icon-watch', badge: null, rating: 5 },
  { id: 11, name: 'Montre Acier Sport', category: 'montres', price: 22000, oldPrice: 27000, icon: 'icon-watch', badge: 'Promo', rating: 4 },
  { id: 12, name: 'Casquette & Ceinture Set', category: 'accessoires', price: 8000, oldPrice: null, icon: 'icon-cap', badge: null, rating: 4 },
];

const money = (n) => n.toLocaleString('fr-FR').replace(/,/g, ' ') + ' FCFA';

/* ============================================================
   RENDU DES PRODUITS
   ============================================================ */
const productGrid = document.getElementById('productGrid');

function renderProducts(filter = 'all') {
  const list = filter === 'all' ? PRODUCTS : PRODUCTS.filter(p => p.category === filter);
  productGrid.innerHTML = list.map(p => `
    <article class="product-card reveal visible" data-id="${p.id}">
      <div class="product-card__media">
        ${p.badge ? `<span class="product-card__badge">${p.badge}</span>` : ''}
        <button class="product-card__quick" aria-label="Aperçu rapide">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/></svg>
        </button>
        <svg class="product-illustration"><use href="#${p.icon}"></use></svg>
      </div>
      <div class="product-card__body">
        <span class="product-card__cat">${p.category}</span>
        <h3 class="product-card__name">${p.name}</h3>
        <div class="product-card__rating">${'★'.repeat(p.rating)}${'☆'.repeat(5 - p.rating)}</div>
        <div class="product-card__footer">
          <span class="product-card__price">${money(p.price)}${p.oldPrice ? `<small>${money(p.oldPrice)}</small>` : ''}</span>
          <button class="add-btn" data-id="${p.id}" aria-label="Ajouter au panier">
            <svg viewBox="0 0 24 24"><path d="M6 6h15l-1.5 9h-12z"/><path d="M6 6L4.5 2H2"/><circle cx="9.5" cy="20" r="1.4"/><circle cx="17.5" cy="20" r="1.4"/></svg>
          </button>
        </div>
      </div>
    </article>
  `).join('');
}

renderProducts();

/* ============================================================
   FILTRES BOUTIQUE
   ============================================================ */
const filterBtns = document.querySelectorAll('.filter-btn');
function applyFilter(filter) {
  filterBtns.forEach(b => b.classList.toggle('active', b.dataset.filter === filter));
  renderProducts(filter);
}
filterBtns.forEach(btn => {
  btn.addEventListener('click', () => applyFilter(btn.dataset.filter));
});

// Liens catégories / footer qui pointent vers un filtre précis
document.querySelectorAll('[data-filter]:not(.filter-btn)').forEach(link => {
  link.addEventListener('click', () => {
    const filter = link.dataset.filter;
    if (!filter) return;
    setTimeout(() => applyFilter(filter), 300);
  });
});

/* ============================================================
   PANIER
   ============================================================ */
let cart = [];
const cartToggle = document.getElementById('cartToggle');
const cartPanel = document.getElementById('cartPanel');
const cartClose = document.getElementById('cartClose');
const cartItemsEl = document.getElementById('cartItems');
const cartTotalEl = document.getElementById('cartTotal');
const cartCountEl = document.getElementById('cartCount');
const overlay = document.getElementById('overlay');
const cartCheckout = document.getElementById('cartCheckout');

function openPanel(panel) {
  panel.classList.add('open');
  overlay.classList.add('show');
}
function closeAllPanels() {
  cartPanel.classList.remove('open');
  overlay.classList.remove('show');
}

cartToggle.addEventListener('click', () => {
  renderCart();
  openPanel(cartPanel);
});
cartClose.addEventListener('click', closeAllPanels);
overlay.addEventListener('click', closeAllPanels);

function addToCart(id) {
  const product = PRODUCTS.find(p => p.id === Number(id));
  if (!product) return;
  const existing = cart.find(item => item.id === product.id);
  if (existing) {
    existing.qty += 1;
  } else {
    cart.push({ ...product, qty: 1 });
  }
  updateCartUI();
  renderCart();
  pulseCartIcon();
}

function pulseCartIcon() {
  cartToggle.classList.remove('pulse');
  void cartToggle.offsetWidth;
  cartToggle.classList.add('pulse');
}

function removeFromCart(id) {
  cart = cart.filter(item => item.id !== Number(id));
  updateCartUI();
  renderCart();
}

function updateCartUI() {
  const totalQty = cart.reduce((sum, i) => sum + i.qty, 0);
  cartCountEl.textContent = totalQty;
}

function renderCart() {
  if (cart.length === 0) {
    cartItemsEl.innerHTML = '<p class="cart-empty">Votre panier est vide.</p>';
    cartTotalEl.textContent = money(0);
    return;
  }
  cartItemsEl.innerHTML = cart.map(item => `
    <div class="cart-item" data-id="${item.id}">
      <div class="cart-item__icon"><svg viewBox="0 0 200 140"><use href="#${item.icon}"></use></svg></div>
      <div class="cart-item__info">
        <strong>${item.name} ${item.qty > 1 ? `× ${item.qty}` : ''}</strong>
        <span>${money(item.price * item.qty)}</span>
      </div>
      <button class="cart-item__remove" data-id="${item.id}" aria-label="Retirer">&times;</button>
    </div>
  `).join('');
  const total = cart.reduce((sum, i) => sum + i.price * i.qty, 0);
  cartTotalEl.textContent = money(total);
}

document.addEventListener('click', (e) => {
  const addBtn = e.target.closest('.add-btn');
  if (addBtn) { addToCart(addBtn.dataset.id); return; }

  const removeBtn = e.target.closest('.cart-item__remove');
  if (removeBtn) { removeFromCart(removeBtn.dataset.id); return; }
});

cartCheckout.addEventListener('click', (e) => {
  if (cart.length === 0) {
    e.preventDefault();
    return;
  }
  const lines = cart.map(i => `- ${i.name} x${i.qty} : ${money(i.price * i.qty)}`).join('\n');
  const total = cart.reduce((sum, i) => sum + i.price * i.qty, 0);
  const message = `Bonjour Fadia Shop, je souhaite commander :\n${lines}\n\nTotal : ${money(total)}`;
  cartCheckout.href = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;
});

/* ============================================================
   RECHERCHE
   ============================================================ */
const searchToggle = document.getElementById('searchToggle');
const searchPanel = document.getElementById('searchPanel');
const searchClose = document.getElementById('searchClose');

searchToggle.addEventListener('click', () => {
  searchPanel.classList.toggle('open');
  if (searchPanel.classList.contains('open')) {
    setTimeout(() => searchPanel.querySelector('input').focus(), 200);
  }
});
searchClose.addEventListener('click', () => searchPanel.classList.remove('open'));

/* ============================================================
   MENU MOBILE
   ============================================================ */
const navToggle = document.getElementById('navToggle');
const mainNav = document.getElementById('mainNav');

navToggle.addEventListener('click', () => {
  navToggle.classList.toggle('open');
  mainNav.classList.toggle('open');
});

document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    navToggle.classList.remove('open');
    mainNav.classList.remove('open');
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
  });
});

/* ============================================================
   PARTAGER / ENREGISTRER (fiche établissement)
   ============================================================ */
const shareBtn = document.getElementById('shareBtn');
const shareToast = document.getElementById('shareToast');
const saveBtn = document.getElementById('saveBtn');

shareBtn.addEventListener('click', async () => {
  const shareData = {
    title: 'Showroom Fadia Shop — Keur Massar',
    text: 'Showroom Fadia Shop : polos, chemises, ensembles et montres pour homme à Keur Massar.',
    url: window.location.href,
  };
  try {
    if (navigator.share) {
      await navigator.share(shareData);
      return;
    }
  } catch (err) {
    if (err && err.name === 'AbortError') return;
  }
  try {
    await navigator.clipboard.writeText(window.location.href);
    shareToast.classList.add('show');
    setTimeout(() => shareToast.classList.remove('show'), 2500);
  } catch (err) {
    // Presse-papier indisponible : rien à faire de plus côté navigateur.
  }
});

const SAVE_KEY = 'fadiaShop.saved';
if (localStorage.getItem(SAVE_KEY) === '1') saveBtn.classList.add('saved');

saveBtn.addEventListener('click', () => {
  const isSaved = saveBtn.classList.toggle('saved');
  localStorage.setItem(SAVE_KEY, isSaved ? '1' : '0');
  saveBtn.querySelector('span:last-child').textContent = isSaved ? 'Enregistré' : 'Enregistrer';
});
if (saveBtn.classList.contains('saved')) {
  saveBtn.querySelector('span:last-child').textContent = 'Enregistré';
}

/* ============================================================
   ONGLETS (Présentation / Avis / Photos) — scrollspy
   ============================================================ */
const tabs = document.querySelectorAll('.tab');
const tabSections = ['presentation', 'avis', 'photos']
  .map(id => document.getElementById(id))
  .filter(Boolean);

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
  });
});

function updateActiveTab() {
  const triggerY = window.scrollY + 160;
  let currentId = tabSections[0] && tabSections[0].id;
  tabSections.forEach(section => {
    if (section.offsetTop <= triggerY) currentId = section.id;
  });
  tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === currentId));
}

window.addEventListener('scroll', updateActiveTab);
updateActiveTab();

/* ============================================================
   SCROLL : header, back-to-top, reveal
   ============================================================ */
const header = document.getElementById('header');
const backToTop = document.getElementById('backToTop');

window.addEventListener('scroll', () => {
  const scrolled = window.scrollY > 40;
  header.style.boxShadow = scrolled ? '0 6px 20px rgba(13,13,13,0.06)' : 'none';
  backToTop.classList.toggle('show', window.scrollY > 500);
});

backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });

document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

/* ============================================================
   ANNÉE FOOTER
   ============================================================ */
document.getElementById('year').textContent = new Date().getFullYear();
