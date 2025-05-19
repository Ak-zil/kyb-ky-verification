// Main application JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // App state
    const state = {
        currentPage: null,
        token: localStorage.getItem('token'),
        userEmail: localStorage.getItem('userEmail'),
        kycPage: 1,
        kybPage: 1,
        kycFilter: '',
        kybFilter: '',
        kycSearch: '',
        kybSearch: '',
        kycData: null,
        kybData: null,
        currentBusinessId: null,
        currentUserId: null,
        currentVerificationId: null,
        currentUboVerificationId: null
    };

    // API base URL
    const API_BASE_URL = '/api';

    // Initialize the application
    init();

    /**
     * Initialize the application
     */
    function init() {
        attachEventListeners();
        
        if (state.token) {
            showAuthenticatedUI();
            navigateToDashboard();
        } else {
            showLoginPage();
        }
    }

    /**
     * Attach event listeners to elements
     */
    function attachEventListeners() {
        // Login form submission
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', handleLogin);
        }

        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleLogout);
        }

        // Sidebar navigation
        const sidebarItems = document.querySelectorAll('.sidebar-item');
        sidebarItems.forEach(item => {
            item.addEventListener('click', function() {
                const page = this.getAttribute('data-page');
                navigateToPage(page);
            });
        });

        // New verification type selection
        const newKycBtn = document.getElementById('new-kyc');
        const newKybBtn = document.getElementById('new-kyb');
        
        if (newKycBtn) {
            newKycBtn.addEventListener('click', showNewKycForm);
        }
        
        if (newKybBtn) {
            newKybBtn.addEventListener('click', showNewKybForm);
        }

        // Cancel buttons for new verification forms
        const cancelKycBtn = document.getElementById('cancel-kyc');
        const cancelKybBtn = document.getElementById('cancel-kyb');
        
        if (cancelKycBtn) {
            cancelKycBtn.addEventListener('click', hideNewVerificationForms);
        }
        
        if (cancelKybBtn) {
            cancelKybBtn.addEventListener('click', hideNewVerificationForms);
        }

        // New verification form submissions
        const newKycForm = document.getElementById('new-kyc-form');
        const newKybForm = document.getElementById('new-kyb-form');
        
        if (newKycForm) {
            newKycForm.addEventListener('submit', handleNewKycSubmit);
        }
        
        if (newKybForm) {
            newKybForm.addEventListener('submit', handleNewKybSubmit);
        }

        // Back buttons
        const backToKycList = document.getElementById('back-to-kyc-list');
        const backToKybList = document.getElementById('back-to-kyb-list');
        const backToKybDetail = document.getElementById('back-to-kyb-detail');
        
        if (backToKycList) {
            backToKycList.addEventListener('click', function() {
                navigateToPage('kyc-list');
            });
        }
        
        if (backToKybList) {
            backToKybList.addEventListener('click', function() {
                navigateToPage('kyb-list');
            });
        }
        
        if (backToKybDetail) {
            backToKybDetail.addEventListener('click', function() {
                showKybDetailPage(state.currentBusinessId);
            });
        }

        // Filter and search for KYC list
        const kycStatusFilter = document.getElementById('kyc-status-filter');
        const kycSearch = document.getElementById('kyc-search');
        const kycSearchBtn = document.getElementById('kyc-search-btn');
        const kycPrevPage = document.getElementById('kyc-prev-page');
        const kycNextPage = document.getElementById('kyc-next-page');
        
        if (kycStatusFilter) {
            kycStatusFilter.addEventListener('change', function() {
                state.kycFilter = this.value;
                state.kycPage = 1;
                loadKycList();
            });
        }
        
        if (kycSearchBtn) {
            kycSearchBtn.addEventListener('click', function() {
                state.kycSearch = kycSearch.value;
                state.kycPage = 1;
                loadKycList();
            });
        }
        
        if (kycSearch) {
            kycSearch.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    state.kycSearch = this.value;
                    state.kycPage = 1;
                    loadKycList();
                }
            });
        }
        
        if (kycPrevPage) {
            kycPrevPage.addEventListener('click', function() {
                if (state.kycPage > 1) {
                    state.kycPage--;
                    loadKycList();
                }
            });
        }
        
        if (kycNextPage) {
            kycNextPage.addEventListener('click', function() {
                if (state.kycData && state.kycData.total > state.kycPage * 10) {
                    state.kycPage++;
                    loadKycList();
                }
            });
        }

        // Filter and search for KYB list
        const kybStatusFilter = document.getElementById('kyb-status-filter');
        const kybSearch = document.getElementById('kyb-search');
        const kybSearchBtn = document.getElementById('kyb-search-btn');
        const kybPrevPage = document.getElementById('kyb-prev-page');
        const kybNextPage = document.getElementById('kyb-next-page');
        
        if (kybStatusFilter) {
            kybStatusFilter.addEventListener('change', function() {
                state.kybFilter = this.value;
                state.kybPage = 1;
                loadKybList();
            });
        }
        
        if (kybSearchBtn) {
            kybSearchBtn.addEventListener('click', function() {
                state.kybSearch = kybSearch.value;
                state.kybPage = 1;
                loadKybList();
            });
        }
        
        if (kybSearch) {
            kybSearch.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    state.kybSearch = this.value;
                    state.kybPage = 1;
                    loadKybList();
                }
            });
        }
        
        if (kybPrevPage) {
            kybPrevPage.addEventListener('click', function() {
                if (state.kybPage > 1) {
                    state.kybPage--;
                    loadKybList();
                }
            });
        }
        
        if (kybNextPage) {
            kybNextPage.addEventListener('click', function() {
                if (state.kybData && state.kybData.total > state.kybPage * 10) {
                    state.kybPage++;
                    loadKybList();
                }
            });
        }

        // Modal close buttons
        const modalClose = document.getElementById('modal-close');
        const modalCancel = document.getElementById('modal-cancel');
        
        if (modalClose) {
            modalClose.addEventListener('click', closeModal);
        }
        
        if (modalCancel) {
            modalCancel.addEventListener('click', closeModal);
        }
    }

    /**
     * Show the specified page and hide all others
     * @param {string} pageName - Name of the page to show
     */
    function showPage(pageName) {
        // Get all pages
        const pages = document.querySelectorAll('.page');
        
        // Get the page we want to show
        const pageToShow = document.getElementById(`${pageName}-page`);
        
        if (pageToShow) {
            // Hide all pages
            pages.forEach(page => {
                page.classList.add('hidden');
            });
            
            // Show the requested page
            pageToShow.classList.remove('hidden');
            
            // Update the page title
            const pageTitle = document.getElementById('page-title');
            if (pageTitle) {
                pageTitle.textContent = formatPageTitle(pageName);
            }
            
            // Update active sidebar item
            const sidebarItems = document.querySelectorAll('.sidebar-item');
            sidebarItems.forEach(item => {
                if (item.getAttribute('data-page') === pageName) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
            
            // Update current page
            state.currentPage = pageName;
        } else {
            console.error(`Page ${pageName}-page not found`);
        }
    }

    /**
     * Format page name for display in title
     * @param {string} pageName - Page name
     * @returns {string} Formatted page title
     */
    function formatPageTitle(pageName) {
        switch (pageName) {
            case 'dashboard':
                return 'Dashboard';
            case 'kyc-list':
                return 'KYC Verifications';
            case 'kyb-list':
                return 'KYB Verifications';
            case 'new-verification':
                return 'New Verification';
            case 'kyc-detail':
                return 'KYC Verification Details';
            case 'kyb-detail':
                return 'KYB Verification Details';
            case 'ubo-detail':
                return 'UBO Verification Details';
            default:
                return 'Verification System';
        }
    }

    /**
     * Show the login page
     */
    function showLoginPage() {
        // Get the page
        const loginPage = document.getElementById('login-page');
        const appContainer = document.querySelector('.app-container');
        
        if (loginPage && appContainer) {
            // Hide the app container
            document.querySelectorAll('.page').forEach(page => {
                page.classList.add('hidden');
            });
            
            // Show the login page
            loginPage.classList.remove('hidden');
            
            // Hide sidebar and header
            document.querySelector('.sidebar').style.display = 'none';
            document.querySelector('.content-header').style.display = 'none';
        }
    }

    /**
     * Show the authenticated UI (sidebar and header)
     */
    function showAuthenticatedUI() {
        // Show sidebar and header
        document.querySelector('.sidebar').style.display = 'flex';
        document.querySelector('.content-header').style.display = 'flex';
        
        // Update user info
        document.getElementById('user-email').textContent = state.userEmail || 'User';
    }

    /**
     * Navigate to the specified page
     * @param {string} pageName - Name of the page to navigate to
     */
    function navigateToPage(pageName) {
        switch (pageName) {
            case 'dashboard':
                navigateToDashboard();
                break;
            case 'kyc-list':
                navigateToKycList();
                break;
            case 'kyb-list':
                navigateToKybList();
                break;
            case 'new-verification':
                navigateToNewVerification();
                break;
            default:
                showPage(pageName);
                break;
        }
    }

    /**
     * Navigate to the dashboard
     */
    function navigateToDashboard() {
        showPage('dashboard');
        loadDashboardData();
    }

    /**
     * Navigate to the KYC list
     */
    function navigateToKycList() {
        showPage('kyc-list');
        loadKycList();
    }

    /**
     * Navigate to the KYB list
     */
    function navigateToKybList() {
        showPage('kyb-list');
        loadKybList();
    }

    /**
     * Navigate to the new verification page
     */
    function navigateToNewVerification() {
        showPage('new-verification');
        hideNewVerificationForms();
        
        // Show the verification type cards
        document.querySelector('.verification-types').classList.remove('hidden');
    }

    /**
     * Show the new KYC verification form
     */
    function showNewKycForm() {
        // Hide verification type cards
        document.querySelector('.verification-types').classList.add('hidden');
        
        // Show KYC form
        const kycFormContainer = document.getElementById('new-kyc-form-container');
        if (kycFormContainer) {
            kycFormContainer.classList.remove('hidden');
        }
        
        // Reset form
        const kycForm = document.getElementById('new-kyc-form');
        if (kycForm) {
            kycForm.reset();
        }
    }

    /**
     * Show the new KYB verification form
     */
    function showNewKybForm() {
        // Hide verification type cards
        document.querySelector('.verification-types').classList.add('hidden');
        
        // Show KYB form
        const kybFormContainer = document.getElementById('new-kyb-form-container');
        if (kybFormContainer) {
            kybFormContainer.classList.remove('hidden');
        }
        
        // Reset form
        const kybForm = document.getElementById('new-kyb-form');
        if (kybForm) {
            kybForm.reset();
        }
    }

    /**
     * Hide all new verification forms
     */
    function hideNewVerificationForms() {
        // Show verification type cards
        document.querySelector('.verification-types').classList.remove('hidden');
        
        // Hide KYC form
        const kycFormContainer = document.getElementById('new-kyc-form-container');
        if (kycFormContainer) {
            kycFormContainer.classList.add('hidden');
        }
        
        // Hide KYB form
        const kybFormContainer = document.getElementById('new-kyb-form-container');
        if (kybFormContainer) {
            kybFormContainer.classList.add('hidden');
        }
    }

    /**
     * Show the KYC detail page
     * @param {string} verificationId - ID of the verification
     */
    function showKycDetailPage(verificationId) {
        state.currentVerificationId = verificationId;
        showPage('kyc-detail');
        loadKycDetail(verificationId);
    }

    /**
     * Show the KYB detail page
     * @param {string} verificationId - ID of the verification
     */
    function showKybDetailPage(verificationId) {
        state.currentVerificationId = verificationId;
        state.currentBusinessId = verificationId; // Store for returning from UBO details
        showPage('kyb-detail');
        loadKybDetail(verificationId);
    }

    /**
     * Show the UBO detail page
     * @param {string} verificationId - ID of the UBO verification
     * @param {string} userId - ID of the UBO user
     */
    function showUboDetailPage(verificationId, userId) {
        state.currentUboVerificationId = verificationId;
        state.currentUserId = userId;
        showPage('ubo-detail');
        loadUboDetail(verificationId);
    }

    /**
     * Handle login form submission
     * @param {Event} e - Form submit event
     */
    async function handleLogin(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    password
                })
            });
            
            if (!response.ok) {
                throw new Error('Login failed');
            }
            
            const data = await response.json();
            
            // Store token and user info
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('userEmail', email);
            
            state.token = data.access_token;
            state.userEmail = email;
            
            // Show authenticated UI
            showAuthenticatedUI();
            
            // Navigate to dashboard
            navigateToDashboard();
            
            // Show success notification
            showToast('Login successful', 'success');
        } catch (error) {
            console.error('Login error:', error);
            document.getElementById('login-error').textContent = 'Invalid email or password';
            document.getElementById('login-error').classList.remove('hidden');
        }
    }

    /**
     * Handle logout
     */
    function handleLogout() {
        // Clear token and user info
        localStorage.removeItem('token');
        localStorage.removeItem('userEmail');
        
        state.token = null;
        state.userEmail = null;
        
        // Show login page
        showLoginPage();
        
        // Show success notification
        showToast('Logged out successfully', 'success');
    }

    /**
     * Handle new KYC verification form submission
     * @param {Event} e - Form submit event
     */
    async function handleNewKycSubmit(e) {
        e.preventDefault();
        
        const userId = document.getElementById('kyc-user-id').value;
        const additionalDataStr = document.getElementById('kyc-additional-data').value;
        
        let additionalData = {};
        
        // Parse additional data if provided
        if (additionalDataStr) {
            try {
                additionalData = JSON.parse(additionalDataStr);
            } catch (error) {
                showToast('Invalid JSON in additional data', 'error');
                return;
            }
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/verify/kyc`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify({
                    user_id: userId,
                    additional_data: additionalData
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to start KYC verification');
            }
            
            const data = await response.json();
            
            // Show success notification
            showToast('KYC verification started successfully', 'success');
            
            // Navigate to KYC list
            navigateToKycList();
        } catch (error) {
            console.error('KYC verification error:', error);
            showToast('Failed to start KYC verification', 'error');
        }
    }

    /**
     * Handle new KYB verification form submission
     * @param {Event} e - Form submit event
     */
    async function handleNewKybSubmit(e) {
        e.preventDefault();
        
        const businessId = document.getElementById('kyb-business-id').value;
        const additionalDataStr = document.getElementById('kyb-additional-data').value;
        
        let additionalData = {};
        
        // Parse additional data if provided
        if (additionalDataStr) {
            try {
                additionalData = JSON.parse(additionalDataStr);
            } catch (error) {
                showToast('Invalid JSON in additional data', 'error');
                return;
            }
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/verify/business`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${state.token}`
                },
                body: JSON.stringify({
                    business_id: businessId,
                    additional_data: additionalData
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to start KYB verification');
            }
            
            const data = await response.json();
            
            // Show success notification
            showToast('KYB verification started successfully', 'success');
            
            // Navigate to KYB list
            navigateToKybList();
        } catch (error) {
            console.error('KYB verification error:', error);
            showToast('Failed to start KYB verification', 'error');
        }
    }

    /**
     * Load dashboard data
     */
    async function loadDashboardData() {
        try {
            // Load KYC count
            const kycResponse = await fetch(`${API_BASE_URL}/verify/kyc/list?limit=1`, {
                headers: {
                    'Authorization': `Bearer ${state.token}`
                }
            });
            
            if (!kycResponse.ok) {
                throw new Error('Failed to load KYC data');
            }
            
            const kycData = await kycResponse.json();
            
            // Load KYB count
            const kybResponse = await fetch(`${API_BASE_URL}/verify/business/list?limit=1`, {
                headers: {
                    'Authorization': `Bearer ${state.token}`
                }
            });
            
            if (!kybResponse.ok) {
                throw new Error('Failed to load KYB data');
            }
            
            const kybData = await kybResponse.json();
            
            // Update dashboard stats
            document.getElementById('kyc-count').textContent = kycData.total || 0;
            document.getElementById('kyb-count').textContent = kybData.total || 0;
            
            // Calculate completed and pending counts
            let completedCount = 0;
            let pendingCount = 0;
            
            // Load recent verifications
            const recentResponse = await fetch(`${API_BASE_URL}/verify/kyc/list?limit=5`, {
                headers: {
                    'Authorization': `Bearer ${state.token}`
                }
            });
            
            if (!recentResponse.ok) {
                throw new Error('Failed to load recent verifications');
            }
            
            const recentData = await recentResponse.json();
            
            // Count completed and pending
            recentData.items.forEach(item => {
                if (item.status === 'completed') {
                    completedCount++;
                } else if (item.status === 'pending' || item.status === 'processing') {
                    pendingCount++;
                }
            });
            
            // Update dashboard stats
            document.getElementById('completed-count').textContent = completedCount;
            document.getElementById('pending-count').textContent = pendingCount;
            
            // Populate recent verifications table
            const recentTableBody = document.getElementById('recent-verifications-body');
            
            if (recentTableBody) {
                recentTableBody.innerHTML = '';
                
                if (recentData.items.length === 0) {
                    const row = document.createElement('tr');
                    row.innerHTML = '<td colspan="5">No recent verifications found</td>';
                    recentTableBody.appendChild(row);
                } else {
                    recentData.items.forEach(item => {
                        const row = document.createElement('tr');
                        
                        const type = item.business_id ? 'KYB' : 'KYC';
                        const id = item.business_id || item.user_id;
                        
                        row.innerHTML = `
                            <td>${item.verification_id.substring(0, 8)}...</td>
                            <td>${type}</td>
                            <td><span class="status-badge ${item.status}">${item.status}</span></td>
                            <td>${formatDate(item.created_at)}</td>
                            <td>
                                <button class="btn-action view-btn" data-id="${item.verification_id}" data-type="${type.toLowerCase()}">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        `;
                        
                        recentTableBody.appendChild(row);
                    });
                    
                    // Add click event listeners to view buttons
                    const viewButtons = recentTableBody.querySelectorAll('.view-btn');
                    viewButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            const id = this.getAttribute('data-id');
                            const type = this.getAttribute('data-type');
                            
                            if (type === 'kyc') {
                                showKycDetailPage(id);
                            } else if (type === 'kyb') {
                                showKybDetailPage(id);
                            }
                        });
                    });
                }
            }
        } catch (error) {
            console.error('Dashboard data error:', error);
            showToast('Failed to load dashboard data', 'error');
        }
    }

    /**
     * Load KYC list
     */
    async function loadKycList() {
        try {
            let url = `${API_BASE_URL}/verify/kyc/list?skip=${(state.kycPage - 1) * 10}&limit=10`;
            
            if (state.kycFilter) {
                url += `&status=${state.kycFilter}`;
            }
            
            // TODO: Add search functionality when API supports it
            
            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${state.token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load KYC list');
            }
            
            const data = await response.json();
            state.kycData = data;
            
            // Update table
            const tableBody = document.getElementById('kyc-table-body');
            
            if (tableBody) {
                tableBody.innerHTML = '';
                
                if (data.items.length === 0) {
                    const row = document.createElement('tr');
                    row.innerHTML = '<td colspan="7">No KYC verifications found</td>';
                    tableBody.appendChild(row);
                } else {
                    data.items.forEach(item => {
                        const row = document.createElement('tr');
                        
                        row.innerHTML = `
                            <td>${item.verification_id.substring(0, 8)}...</td>
                            <td>${item.user_id}</td>
                            <td><span class="status-badge ${item.status}">${item.status}</span></td>
                            <td>${item.result ? `<span class="result-badge ${item.result}">${item.result}</span>` : '-'}</td>
                            <td>${formatDate(item.created_at)}</td>
                            <td>${item.completed_at ? formatDate(item.completed_at) : '-'}</td>
                            <td>
                                <button class="btn-action view-btn" data-id="${item.verification_id}">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        `;
                        
                        tableBody.appendChild(row);
                    });
                    
                    // Add click event listeners to view buttons
                    const viewButtons = tableBody.querySelectorAll('.view-btn');
                    viewButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            const id = this.getAttribute('data-id');
                            showKycDetailPage(id);
                        });
                    });
                }
            }
            
            // Update pagination
            const pageInfo = document.getElementById('kyc-page-info');
            if (pageInfo) {
                const totalPages = Math.ceil(data.total / 10);
                pageInfo.textContent = `Page ${state.kycPage} of ${totalPages || 1}`;
            }
            
            // Update prev/next buttons
            const prevBtn = document.getElementById('kyc-prev-page');
            const nextBtn = document.getElementById('kyc-next-page');
            
            if (prevBtn) {
                prevBtn.disabled = state.kycPage <= 1;
            }
            
            if (nextBtn) {
                nextBtn.disabled = !data.items.length || data.items.length < 10;
            }
        } catch (error) {
            console.error('KYC list error:', error);
            showToast('Failed to load KYC list', 'error');
        }
    }

    /**
     * Load KYB list
     */
    async function loadKybList() {
        try {
            let url = `${API_BASE_URL}/verify/business/list?skip=${(state.kybPage - 1) * 10}&limit=10`;
            
            if (state.kybFilter) {
                url += `&status=${state.kybFilter}`;
            }
            
            // TODO: Add search functionality when API supports it
            
            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${state.token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load KYB list');
            }
            
            const data = await response.json();
            state.kybData = data;
            
            // Update table
            const tableBody = document.getElementById('kyb-table-body');
            
            if (tableBody) {
                tableBody.innerHTML = '';
                
                if (data.items.length === 0) {
                    const row = document.createElement('tr');
                    row.innerHTML = '<td colspan="7">No KYB verifications found</td>';
                    tableBody.appendChild(row);
                } else {
                    data.items.forEach(item => {
                        const row = document.createElement('tr');
                        
                        row.innerHTML = `
                            <td>${item.verification_id.substring(0, 8)}...</td>
                            <td>${item.business_id}</td>
                            <td><span class="status-badge ${item.status}">${item.status}</span></td>
                            <td>${item.result ? `<span class="result-badge ${item.result}">${item.result}</span>` : '-'}</td>
                            <td>${formatDate(item.created_at)}</td>
                            <td>${item.completed_at ? formatDate(item.completed_at) : '-'}</td>
                            <td>
                                <button class="btn-action view-btn" data-id="${item.verification_id}">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </td>
                        `;
                        
                        tableBody.appendChild(row);
                    });
                    
                    // Add click event listeners to view buttons
                    const viewButtons = tableBody.querySelectorAll('.view-btn');
                    viewButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            const id = this.getAttribute('data-id');
                            showKybDetailPage(id);
                        });
                    });
                }
            }
            
            // Update pagination
            const pageInfo = document.getElementById('kyb-page-info');
            if (pageInfo) {
                const totalPages = Math.ceil(data.total / 10);
                pageInfo.textContent = `Page ${state.kybPage} of ${totalPages || 1}`;
            }
            
            // Update prev/next buttons
            const prevBtn = document.getElementById('kyb-prev-page');
            const nextBtn = document.getElementById('kyb-next-page');
            
            if (prevBtn) {
                prevBtn.disabled = state.kybPage <= 1;
            }
            
            if (nextBtn) {
                nextBtn.disabled = !data.items.length || data.items.length < 10;
            }
        } catch (error) {
            console.error('KYB list error:', error);
            showToast('Failed to load KYB list', 'error');
        }
    }

    /**
     * Load KYC verification details
     * @param {string} verificationId - ID of the verification
     */
    async function loadKycDetail(verificationId) {
        try {
            // Clear existing content
            document.getElementById('kyc-detail-id').textContent = '';
            document.getElementById('kyc-detail-user-id').textContent = '';
            document.getElementById('kyc-detail-created').textContent = '';
            document.getElementById('kyc-detail-completed').textContent = '';
            document.getElementById('kyc-detail-summary').textContent = '';
            document.getElementById('kyc-initial-diligence-checks').innerHTML = '';
            document.getElementById('kyc-gov-id-checks').innerHTML = '';
            document.getElementById('kyc-additional-checks').innerHTML = '';
            
            // Fetch verification details
            const response = await fetch(`${API_BASE_URL}/verify/report/detail/${verificationId}`, {
                headers: {
                    'Authorization': `Bearer ${state.token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load KYC details');
            }
            
            const data = await response.json();
            
            // Update page content
            document.getElementById('kyc-detail-id').textContent = data.verification_id;
            document.getElementById('kyc-detail-user-id').textContent = data.results.user_id || 'N/A';
            document.getElementById('kyc-detail-created').textContent = formatDate(data.created_at);
            document.getElementById('kyc-detail-completed').textContent = data.completed_at ? formatDate(data.completed_at) : 'In progress';
            document.getElementById('kyc-detail-summary').textContent = data.results.summary || 'No summary available';
            
            // Update status badges
            const statusBadge = document.getElementById('kyc-detail-status-badge');
            statusBadge.textContent = data.status;
            statusBadge.className = 'status-badge ' + data.status;
            
            const resultBadge = document.getElementById('kyc-detail-result-badge');
            if (data.results.overall_status) {
                resultBadge.textContent = data.results.overall_status;
                resultBadge.className = 'result-badge ' + data.results.overall_status;
                resultBadge.style.display = '';
            } else {
                resultBadge.style.display = 'none';
            }
            
            // Group checks by agent type
            const initialDiligenceChecks = [];
            const govIdChecks = [];
            const additionalChecks = [];
            
            if (data.results.verification_checks) {
                data.results.verification_checks.forEach(check => {
                    if (check.agent_type === 'InitialDiligenceAgent') {
                        initialDiligenceChecks.push(check);
                    } else if (check.agent_type === 'GovtIdVerificationAgent' || check.agent_type === 'IdCheckAgent') {
                        govIdChecks.push(check);
                    } else {
                        additionalChecks.push(check);
                    }
                });
            }
            
            // Populate check sections
            populateCheckList('kyc-initial-diligence-checks', initialDiligenceChecks);
            populateCheckList('kyc-gov-id-checks', govIdChecks);
            populateCheckList('kyc-additional-checks', additionalChecks);
        } catch (error) {
            console.error('KYC detail error:', error);
            showToast('Failed to load KYC details', 'error');
        }
    }

    /**
     * Load KYB verification details
     * @param {string} verificationId - ID of the verification
     */
    async function loadKybDetail(verificationId) {
        try {
            // Clear existing content
            document.getElementById('kyb-detail-id').textContent = '';
            document.getElementById('kyb-detail-business-id').textContent = '';
            document.getElementById('kyb-detail-created').textContent = '';
            document.getElementById('kyb-detail-completed').textContent = '';
            document.getElementById('kyb-detail-summary').textContent = '';
            document.getElementById('kyb-normal-diligence-checks').innerHTML = '';
            document.getElementById('kyb-irs-match-checks').innerHTML = '';
            document.getElementById('kyb-sos-filings-checks').innerHTML = '';
            document.getElementById('kyb-additional-checks').innerHTML = '';
            document.getElementById('kyb-ubo-list').innerHTML = '';
            
            // Fetch verification details
            const response = await fetch(`${API_BASE_URL}/verify/report/detail/${verificationId}`, {
                headers: {
                    'Authorization': `Bearer ${state.token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load KYB details');
            }
            
            const data = await response.json();
            
            // Update page content
            document.getElementById('kyb-detail-id').textContent = data.verification_id;
            document.getElementById('kyb-detail-business-id').textContent = data.results.business_id || 'N/A';
            document.getElementById('kyb-detail-created').textContent = formatDate(data.created_at);
            document.getElementById('kyb-detail-completed').textContent = data.completed_at ? formatDate(data.completed_at) : 'In progress';
            document.getElementById('kyb-detail-summary').textContent = data.results.summary || 'No summary available';
            
            // Update status badges
            const statusBadge = document.getElementById('kyb-detail-status-badge');
            statusBadge.textContent = data.status;
            statusBadge.className = 'status-badge ' + data.status;
            
            const resultBadge = document.getElementById('kyb-detail-result-badge');
            if (data.results.overall_status) {
                resultBadge.textContent = data.results.overall_status;
                resultBadge.className = 'result-badge ' + data.results.overall_status;
                resultBadge.style.display = '';
            } else {
                resultBadge.style.display = 'none';
            }
            
            // Group checks by agent type
            const normalDiligenceChecks = [];
            const irsMatchChecks = [];
            const sosFilingsChecks = [];
            const additionalChecks = [];
            
            if (data.results.verification_checks) {
                data.results.verification_checks.forEach(check => {
                    if (check.agent_type === 'NormalDiligenceAgent') {
                        normalDiligenceChecks.push(check);
                    } else if (check.agent_type === 'IrsMatchAgent') {
                        irsMatchChecks.push(check);
                    } else if (check.agent_type === 'SosFilingsAgent') {
                        sosFilingsChecks.push(check);
                    } else {
                        additionalChecks.push(check);
                    }
                });
            }
            
            // Populate check sections
            populateCheckList('kyb-normal-diligence-checks', normalDiligenceChecks);
            populateCheckList('kyb-irs-match-checks', irsMatchChecks);
            populateCheckList('kyb-sos-filings-checks', sosFilingsChecks);
            populateCheckList('kyb-additional-checks', additionalChecks);
            
            // Populate UBO list
            const uboList = document.getElementById('kyb-ubo-list');
            
            if (uboList) {
                uboList.innerHTML = '';
                
                if (!data.results.ubo_reports || data.results.ubo_reports.length === 0) {
                    uboList.innerHTML = '<p>No UBOs found</p>';
                } else {
                    data.results.ubo_reports.forEach(ubo => {
                        const uboCard = document.createElement('div');
                        uboCard.className = 'ubo-card';
                        
                        uboCard.innerHTML = `
                            <div class="ubo-header">
                                <h4>UBO ID: ${ubo.user_id}</h4>
                                <span class="status-badge ${ubo.status}">${ubo.status}</span>
                                ${ubo.result ? `<span class="result-badge ${ubo.result}">${ubo.result}</span>` : ''}
                            </div>
                            <div class="ubo-body">
                                <p>${ubo.reason || 'No details available'}</p>
                            </div>
                            <div class="ubo-footer">
                                <button class="btn-secondary view-ubo-btn" data-id="${ubo.verification_id}" data-user-id="${ubo.user_id}">View Details</button>
                            </div>
                        `;
                        
                        uboList.appendChild(uboCard);
                    });
                    
                    // Add click event listeners to UBO view buttons
                    const uboViewButtons = uboList.querySelectorAll('.view-ubo-btn');
                    uboViewButtons.forEach(button => {
                        button.addEventListener('click', function() {
                            const id = this.getAttribute('data-id');
                            const userId = this.getAttribute('data-user-id');
                            showUboDetailPage(id, userId);
                        });
                    });
                }
            }
        } catch (error) {
            console.error('KYB detail error:', error);
            showToast('Failed to load KYB details', 'error');
        }
    }

    /**
     * Load UBO verification details
     * @param {string} verificationId - ID of the UBO verification
     */
    async function loadUboDetail(verificationId) {
        try {
            // Clear existing content
            document.getElementById('ubo-detail-id').textContent = '';
            document.getElementById('ubo-detail-user-id').textContent = '';
            document.getElementById('ubo-detail-created').textContent = '';
            document.getElementById('ubo-detail-completed').textContent = '';
            document.getElementById('ubo-detail-summary').textContent = '';
            document.getElementById('ubo-initial-diligence-checks').innerHTML = '';
            document.getElementById('ubo-gov-id-checks').innerHTML = '';
            document.getElementById('ubo-additional-checks').innerHTML = '';
            
            // Fetch verification details
            const response = await fetch(`${API_BASE_URL}/verify/report/detail/${verificationId}`, {
                headers: {
                    'Authorization': `Bearer ${state.token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load UBO details');
            }
            
            const data = await response.json();
            
            // Update page content
            document.getElementById('ubo-detail-id').textContent = data.verification_id;
            document.getElementById('ubo-detail-user-id').textContent = state.currentUserId || 'N/A';
            document.getElementById('ubo-detail-created').textContent = formatDate(data.created_at);
            document.getElementById('ubo-detail-completed').textContent = data.completed_at ? formatDate(data.completed_at) : 'In progress';
            document.getElementById('ubo-detail-summary').textContent = data.results.summary || 'No summary available';
            
            // Update status badges
            const statusBadge = document.getElementById('ubo-detail-status-badge');
            statusBadge.textContent = data.status;
            statusBadge.className = 'status-badge ' + data.status;
            
            const resultBadge = document.getElementById('ubo-detail-result-badge');
            if (data.results.overall_status) {
                resultBadge.textContent = data.results.overall_status;
                resultBadge.className = 'result-badge ' + data.results.overall_status;
                resultBadge.style.display = '';
            } else {
                resultBadge.style.display = 'none';
            }
            
            // Group checks by agent type
            const initialDiligenceChecks = [];
            const govIdChecks = [];
            const additionalChecks = [];
            
            if (data.results.verification_checks) {
                data.results.verification_checks.forEach(check => {
                    if (check.agent_type === 'InitialDiligenceAgent') {
                        initialDiligenceChecks.push(check);
                    } else if (check.agent_type === 'GovtIdVerificationAgent' || check.agent_type === 'IdCheckAgent') {
                        govIdChecks.push(check);
                    } else {
                        additionalChecks.push(check);
                    }
                });
            }
            
            // Populate check sections
            populateCheckList('ubo-initial-diligence-checks', initialDiligenceChecks);
            populateCheckList('ubo-gov-id-checks', govIdChecks);
            populateCheckList('ubo-additional-checks', additionalChecks);
        } catch (error) {
            console.error('UBO detail error:', error);
            showToast('Failed to load UBO details', 'error');
        }
    }

    /**
     * Populate a check list with checks
     * @param {string} containerId - ID of the container element
     * @param {Array} checks - Array of check objects
     */
    function populateCheckList(containerId, checks) {
        const container = document.getElementById(containerId);
        
        if (container) {
            if (!checks || checks.length === 0) {
                container.innerHTML = '<p>No checks found</p>';
                return;
            }
            
            container.innerHTML = '';
            
            checks.forEach(check => {
                const checkItem = document.createElement('div');
                checkItem.className = 'check-item';
                
                checkItem.innerHTML = `
                    <div class="check-header">
                        <h5>${check.check_name}</h5>
                        <span class="check-status ${check.status}">${check.status}</span>
                    </div>
                    <div class="check-details">
                        <p>${check.details || 'No details available'}</p>
                    </div>
                `;
                
                container.appendChild(checkItem);
            });
        }
    }

    /**
     * Show the modal with custom content and actions
     * @param {string} title - Modal title
     * @param {string} content - Modal content
     * @param {Function} confirmCallback - Callback for confirm button
     */
    function showModal(title, content, confirmCallback) {
        const modalOverlay = document.getElementById('modal-overlay');
        const modalTitle = document.getElementById('modal-title');
        const modalContent = document.getElementById('modal-content');
        const modalConfirm = document.getElementById('modal-confirm');
        
        modalTitle.textContent = title;
        modalContent.innerHTML = content;
        
        // Set up confirm button
        if (confirmCallback) {
            modalConfirm.style.display = '';
            modalConfirm.addEventListener('click', function modalConfirmHandler() {
                confirmCallback();
                closeModal();
                modalConfirm.removeEventListener('click', modalConfirmHandler);
            });
        } else {
            modalConfirm.style.display = 'none';
        }
        
        // Show modal
        modalOverlay.classList.remove('hidden');
    }

    /**
     * Close the modal
     */
    function closeModal() {
        const modalOverlay = document.getElementById('modal-overlay');
        modalOverlay.classList.add('hidden');
    }

    /**
     * Show a toast notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type (success, error, warning, info)
     */
    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = getToastIcon(type);
        
        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close"><i class="fas fa-times"></i></button>
        `;
        
        toastContainer.appendChild(toast);
        
        // Add close button event listener
        toast.querySelector('.toast-close').addEventListener('click', function() {
            toastContainer.removeChild(toast);
        });
        
        // Automatically remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode === toastContainer) {
                toastContainer.removeChild(toast);
            }
        }, 5000);
    }

    /**
     * Get the icon for a toast notification
     * @param {string} type - Notification type
     * @returns {string} Icon HTML
     */
    function getToastIcon(type) {
        switch (type) {
            case 'success':
                return '<i class="fas fa-check-circle"></i>';
            case 'error':
                return '<i class="fas fa-exclamation-circle"></i>';
            case 'warning':
                return '<i class="fas fa-exclamation-triangle"></i>';
            case 'info':
            default:
                return '<i class="fas fa-info-circle"></i>';
        }
    }

    /**
     * Format a date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date string
     */
    function formatDate(dateString) {
        if (!dateString) return '-';
        
        const date = new Date(dateString);
        
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        }).format(date);
    }
});