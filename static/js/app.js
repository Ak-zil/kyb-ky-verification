// Global state and configuration
const API_BASE_URL = '/api';
let authToken = localStorage.getItem('authToken');
let currentUser = null;
let currentKycPage = 1;
let currentKybPage = 1;
let kycVerifications = [];
let kybVerifications = [];
let currentKycLimit = 20;
let currentKybLimit = 20;
let currentVerificationId = null;
let currentUboVerificationId = null;
let parentBusinessVerificationId = null;

// DOM elements
const pages = {
    login: document.getElementById('login-page'),
    dashboard: document.getElementById('dashboard-page'),
    kycList: document.getElementById('kyc-list-page'),
    kybList: document.getElementById('kyb-list-page'),
    newVerification: document.getElementById('new-verification-page'),
    kycDetail: document.getElementById('kyc-detail-page'),
    kybDetail: document.getElementById('kyb-detail-page'),
    uboDetail: document.getElementById('ubo-detail-page')
};

// Helper functions
function setAuthToken(token) {
    authToken = token;
    localStorage.setItem('authToken', token);
}

function clearAuthToken() {
    authToken = null;
    localStorage.removeItem('authToken');
}

async function fetchApi(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Add auth header if token exists
    if (authToken) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${authToken}`
        };
    }
    
    try {
        const response = await fetch(url, options);
        
        // Handle unauthorized (token expired)
        if (response.status === 401) {
            clearAuthToken();
            showLoginPage();
            showToast('Session expired. Please login again.', 'warning');
            return null;
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'An error occurred');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'error');
        return null;
    }
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function showPage(pageId) {
    // Hide all pages
    Object.values(pages).forEach(page => page.classList.add('hidden'));
    
    // Show the requested page
    pages[pageId].classList.remove('hidden');
    
    // Update active sidebar item
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageId) {
            item.classList.add('active');
        }
    });
    
    // Update page title
    const pageTitles = {
        dashboard: 'Dashboard',
        kycList: 'KYC Verifications',
        kybList: 'KYB Verifications',
        newVerification: 'New Verification',
        kycDetail: 'KYC Verification Details',
        kybDetail: 'KYB Verification Details',
        uboDetail: 'UBO Verification Details'
    };
    
    document.getElementById('page-title').textContent = pageTitles[pageId] || 'Dashboard';
}

function showLoginPage() {
    document.querySelector('.sidebar').style.display = 'none';
    document.querySelector('.content-header').style.display = 'none';
    showPage('login');
}

function showDashboard() {
    document.querySelector('.sidebar').style.display = 'flex';
    document.querySelector('.content-header').style.display = 'flex';
    showPage('dashboard');
    loadDashboardData();
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.classList.add('toast', `toast-${type}`);
    
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    
    toast.innerHTML = `
        <div class="toast-icon"><i class="${icons[type]}"></i></div>
        <div class="toast-message">${message}</div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    }, 5000);
}

function createStatusBadge(status) {
    const badge = document.createElement('span');
    badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    badge.classList.add('status-badge', `status-${status.toLowerCase()}`);
    return badge;
}

function createResultBadge(result) {
    if (!result) return '';
    
    const badge = document.createElement('span');
    badge.textContent = result.charAt(0).toUpperCase() + result.slice(1);
    badge.classList.add('result-badge', `result-${result.toLowerCase()}`);
    return badge;
}

// Login functionality
document.getElementById('login-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }
        
        const data = await response.json();
        setAuthToken(data.access_token);
        
        // Get user info
        const userInfo = await fetchApi('/auth/me');
        if (userInfo) {
            currentUser = userInfo;
            document.getElementById('user-email').textContent = userInfo.email;
        }
        
        showToast('Login successful', 'success');
        showDashboard();
    } catch (error) {
        document.getElementById('login-error').textContent = error.message;
        document.getElementById('login-error').classList.remove('hidden');
    }
});

// Logout
document.getElementById('logout-btn').addEventListener('click', function() {
    clearAuthToken();
    currentUser = null;
    showLoginPage();
    showToast('Logged out successfully', 'info');
});

// Dashboard data loading
async function loadDashboardData() {
    try {
        // Load counts
        const [kycResponse, kybResponse] = await Promise.all([
            fetchApi('/verify/kyc/list?limit=1'),
            fetchApi('/verify/business/list?limit=1')
        ]);
        
        if (kycResponse) {
            document.getElementById('kyc-count').textContent = kycResponse.total;
        }
        
        if (kybResponse) {
            document.getElementById('kyb-count').textContent = kybResponse.total;
        }
        
        // Calculate completed and pending counts
        let completedCount = 0;
        let pendingCount = 0;
        
        const [completedResponse, pendingResponse] = await Promise.all([
            fetchApi('/verify/kyc/list?status=completed&limit=1'),
            fetchApi('/verify/kyc/list?status=pending&limit=1')
        ]);
        
        if (completedResponse) {
            completedCount += completedResponse.total;
        }
        
        if (pendingResponse) {
            pendingCount += pendingResponse.total;
        }
        
        const [kybCompletedResponse, kybPendingResponse] = await Promise.all([
            fetchApi('/verify/business/list?status=completed&limit=1'),
            fetchApi('/verify/business/list?status=pending&limit=1')
        ]);
        
        if (kybCompletedResponse) {
            completedCount += kybCompletedResponse.total;
        }
        
        if (kybPendingResponse) {
            pendingCount += kybPendingResponse.total;
        }
        
        document.getElementById('completed-count').textContent = completedCount;
        document.getElementById('pending-count').textContent = pendingCount;
        
        // Load recent verifications
        const recentVerifications = await Promise.all([
            fetchApi('/verify/kyc/list?limit=5'),
            fetchApi('/verify/business/list?limit=5')
        ]);
        
        const combinedVerifications = [];
        
        if (recentVerifications[0] && recentVerifications[0].items) {
            recentVerifications[0].items.forEach(v => {
                combinedVerifications.push({
                    ...v,
                    type: 'KYC'
                });
            });
        }
        
        if (recentVerifications[1] && recentVerifications[1].items) {
            recentVerifications[1].items.forEach(v => {
                combinedVerifications.push({
                    ...v,
                    type: 'KYB'
                });
            });
        }
        
        // Sort by created_at date
        combinedVerifications.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        // Take the 10 most recent
        const recentItems = combinedVerifications.slice(0, 10);
        
        const tableBody = document.getElementById('recent-verifications-body');
        tableBody.innerHTML = '';
        
        recentItems.forEach(item => {
            const row = document.createElement('tr');
            
            const idCell = document.createElement('td');
            idCell.textContent = item.verification_id.substring(0, 8) + '...';
            
            const typeCell = document.createElement('td');
            typeCell.textContent = item.type;
            
            const statusCell = document.createElement('td');
            statusCell.appendChild(createStatusBadge(item.status));
            
            const dateCell = document.createElement('td');
            dateCell.textContent = formatDate(item.created_at);
            
            const actionsCell = document.createElement('td');
            const viewBtn = document.createElement('button');
            viewBtn.classList.add('btn-action');
            viewBtn.textContent = 'View';
            viewBtn.addEventListener('click', () => {
                if (item.type === 'KYC') {
                    currentVerificationId = item.verification_id;
                    loadKycDetails(item.verification_id);
                } else {
                    currentVerificationId = item.verification_id;
                    loadKybDetails(item.verification_id);
                }
            });
            actionsCell.appendChild(viewBtn);
            
            row.appendChild(idCell);
            row.appendChild(typeCell);
            row.appendChild(statusCell);
            row.appendChild(dateCell);
            row.appendChild(actionsCell);
            
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showToast('Error loading dashboard data', 'error');
    }
}

// KYC Listing
async function loadKycList() {
    try {
        const status = document.getElementById('kyc-status-filter').value;
        const searchQuery = document.getElementById('kyc-search').value;
        
        // For a real implementation, you would pass the search query to the API
        // Since we don't have search parameter in our API, we'll filter client-side
        
        const response = await fetchApi(`/verify/kyc/list?limit=${currentKycLimit}&skip=${(currentKycPage - 1) * currentKycLimit}${status ? `&status=${status}` : ''}`);
        
        if (!response) return;
        
        kycVerifications = response.items;
        
        const tableBody = document.getElementById('kyc-table-body');
        tableBody.innerHTML = '';
        
        // Client-side filtering for search
        const filteredItems = searchQuery 
            ? kycVerifications.filter(item => 
                item.verification_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (item.user_id && item.user_id.toLowerCase().includes(searchQuery.toLowerCase()))
              )
            : kycVerifications;
        
        filteredItems.forEach(item => {
            const row = document.createElement('tr');
            
            const idCell = document.createElement('td');
            idCell.textContent = item.verification_id.substring(0, 8) + '...';
            
            const userIdCell = document.createElement('td');
            userIdCell.textContent = item.user_id || 'N/A';
            
            const statusCell = document.createElement('td');
            statusCell.appendChild(createStatusBadge(item.status));
            
            const resultCell = document.createElement('td');
            if (item.result) {
                resultCell.appendChild(createResultBadge(item.result));
            } else {
                resultCell.textContent = 'N/A';
            }
            
            const createdCell = document.createElement('td');
            createdCell.textContent = formatDate(item.created_at);
            
            const completedCell = document.createElement('td');
            completedCell.textContent = formatDate(item.completed_at);
            
            const actionsCell = document.createElement('td');
            const viewBtn = document.createElement('button');
            viewBtn.classList.add('btn-action');
            viewBtn.textContent = 'View';
            viewBtn.addEventListener('click', () => {
                currentVerificationId = item.verification_id;
                loadKycDetails(item.verification_id);
            });
            actionsCell.appendChild(viewBtn);
            
            row.appendChild(idCell);
            row.appendChild(userIdCell);
            row.appendChild(statusCell);
            row.appendChild(resultCell);
            row.appendChild(createdCell);
            row.appendChild(completedCell);
            row.appendChild(actionsCell);
            
            tableBody.appendChild(row);
        });
        
        // Update pagination
        const totalPages = Math.ceil(response.total / currentKycLimit);
        document.getElementById('kyc-page-info').textContent = `Page ${currentKycPage} of ${totalPages || 1}`;
        
        document.getElementById('kyc-prev-page').disabled = currentKycPage <= 1;
        document.getElementById('kyc-next-page').disabled = currentKycPage >= totalPages;
    } catch (error) {
        console.error('Error loading KYC list:', error);
        showToast('Error loading KYC verifications', 'error');
    }
}

// KYB Listing
async function loadKybList() {
    try {
        const status = document.getElementById('kyb-status-filter').value;
        const searchQuery = document.getElementById('kyb-search').value;
        
        const response = await fetchApi(`/verify/business/list?limit=${currentKybLimit}&skip=${(currentKybPage - 1) * currentKybLimit}${status ? `&status=${status}` : ''}`);
        
        if (!response) return;
        
        kybVerifications = response.items;
        
        const tableBody = document.getElementById('kyb-table-body');
        tableBody.innerHTML = '';
        
        // Client-side filtering for search
        const filteredItems = searchQuery 
            ? kybVerifications.filter(item => 
                item.verification_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (item.business_id && item.business_id.toLowerCase().includes(searchQuery.toLowerCase()))
              )
            : kybVerifications;
        
        filteredItems.forEach(item => {
            const row = document.createElement('tr');
            
            const idCell = document.createElement('td');
            idCell.textContent = item.verification_id.substring(0, 8) + '...';
            
            const businessIdCell = document.createElement('td');
            businessIdCell.textContent = item.business_id || 'N/A';
            
            const statusCell = document.createElement('td');
            statusCell.appendChild(createStatusBadge(item.status));
            
            const resultCell = document.createElement('td');
            if (item.result) {
                resultCell.appendChild(createResultBadge(item.result));
            } else {
                resultCell.textContent = 'N/A';
            }
            
            const createdCell = document.createElement('td');
            createdCell.textContent = formatDate(item.created_at);
            
            const completedCell = document.createElement('td');
            completedCell.textContent = formatDate(item.completed_at);
            
            const actionsCell = document.createElement('td');
            const viewBtn = document.createElement('button');
            viewBtn.classList.add('btn-action');
            viewBtn.textContent = 'View';
            viewBtn.addEventListener('click', () => {
                currentVerificationId = item.verification_id;
                loadKybDetails(item.verification_id);
            });
            actionsCell.appendChild(viewBtn);
            
            row.appendChild(idCell);
            row.appendChild(businessIdCell);
            row.appendChild(statusCell);
            row.appendChild(resultCell);
            row.appendChild(createdCell);
            row.appendChild(completedCell);
            row.appendChild(actionsCell);
            
            tableBody.appendChild(row);
        });
        
        // Update pagination
        const totalPages = Math.ceil(response.total / currentKybLimit);
        document.getElementById('kyb-page-info').textContent = `Page ${currentKybPage} of ${totalPages || 1}`;
        
        document.getElementById('kyb-prev-page').disabled = currentKybPage <= 1;
        document.getElementById('kyb-next-page').disabled = currentKybPage >= totalPages;
    } catch (error) {
        console.error('Error loading KYB list:', error);
        showToast('Error loading KYB verifications', 'error');
    }
}

// KYC Details 
async function loadKycDetails(verificationId) {
    try {
        const response = await fetchApi(`/verify/report/detail/${verificationId}`);
        
        if (!response) return;
        
        // Update header info
        document.getElementById('kyc-detail-id').textContent = response.verification_id;
        document.getElementById('kyc-detail-user-id').textContent = response.verification_id.split('-')[0] || 'N/A';
        document.getElementById('kyc-detail-created').textContent = formatDate(response.created_at);
        document.getElementById('kyc-detail-completed').textContent = formatDate(response.completed_at);
        
        // Status and result badges - fix the null element issue
        const statusBadge = createStatusBadge(response.status);
        const statusBadgeElement = document.getElementById('kyc-detail-status-badge');
        if (statusBadgeElement) {
            statusBadgeElement.replaceWith(statusBadge);
            statusBadge.id = 'kyc-detail-status-badge';
        } else {
            console.warn("Element 'kyc-detail-status-badge' not found");
            // Find the parent element and append
            const detailStatus = document.querySelector('.detail-status');
            if (detailStatus) {
                statusBadge.id = 'kyc-detail-status-badge';
                detailStatus.appendChild(statusBadge);
            }
        }
        
        if (response.results.overall_status) {
            const resultBadge = createResultBadge(response.results.overall_status);
            const resultBadgeElement = document.getElementById('kyc-detail-result-badge');
            if (resultBadgeElement) {
                resultBadgeElement.replaceWith(resultBadge);
                resultBadge.id = 'kyc-detail-result-badge';
            } else {
                console.warn("Element 'kyc-detail-result-badge' not found");
                // Find the parent element and append
                const detailStatus = document.querySelector('.detail-status');
                if (detailStatus) {
                    resultBadge.id = 'kyc-detail-result-badge';
                    detailStatus.appendChild(resultBadge);
                }
            }
        }
        
        // Summary
        document.getElementById('kyc-detail-summary').textContent = response.results.summary || 'No summary available';
        
        // Group checks by agent type
        const checksByAgent = {};
        response.results.verification_checks.forEach(check => {
            if (!checksByAgent[check.agent_type]) {
                checksByAgent[check.agent_type] = [];
            }
            checksByAgent[check.agent_type].push(check);
        });
        
        // Clear existing checks
        document.getElementById('kyc-initial-diligence-checks').innerHTML = '';
        document.getElementById('kyc-gov-id-checks').innerHTML = '';
        document.getElementById('kyc-additional-checks').innerHTML = '';
        
        // Populate initial diligence checks
        const initialDiligenceChecks = checksByAgent['InitialDiligenceAgent'] || [];
        initialDiligenceChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('kyc-initial-diligence-checks').appendChild(checkItem);
        });
        
        // Populate gov id checks
        const govIdChecks = [
            ...(checksByAgent['GovtIdVerificationAgent'] || []),
            ...(checksByAgent['IdSelfieVerificationAgent'] || []),
            ...(checksByAgent['IdCheckAgent'] || [])
        ];
        govIdChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('kyc-gov-id-checks').appendChild(checkItem);
        });
        
        // Populate additional checks
        const additionalCheckAgents = ['AamvaVerificationAgent', 'EmailPhoneIpVerificationAgent', 
                                      'PaymentBehaviorAgent', 'LoginActivitiesAgent',
                                      'SiftVerificationAgent', 'OfacVerificationAgent'];
        
        const additionalChecks = [];
        additionalCheckAgents.forEach(agent => {
            if (checksByAgent[agent]) {
                additionalChecks.push(...checksByAgent[agent]);
            }
        });
        
        additionalChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('kyc-additional-checks').appendChild(checkItem);
        });
        
        // Show the page
        showPage('kycDetail');
    } catch (error) {
        console.error('Error loading KYC details:', error);
        showToast('Error loading verification details', 'error');
    }
}

// KYB Details
async function loadKybDetails(verificationId) {
    try {
        const response = await fetchApi(`/verify/report/detail/${verificationId}`);
        
        if (!response) return;
        
        // Update header info
        document.getElementById('kyb-detail-id').textContent = response.verification_id;
        document.getElementById('kyb-detail-business-id').textContent = response.verification_id.split('-')[0] || 'N/A';
        document.getElementById('kyb-detail-created').textContent = formatDate(response.created_at);
        document.getElementById('kyb-detail-completed').textContent = formatDate(response.completed_at);
        
        // Status and result badges - fix the null element issue
        const statusBadge = createStatusBadge(response.status);
        const statusBadgeElement = document.getElementById('kyb-detail-status-badge');
        if (statusBadgeElement) {
            statusBadgeElement.replaceWith(statusBadge);
            statusBadge.id = 'kyb-detail-status-badge';
        } else {
            console.warn("Element 'kyb-detail-status-badge' not found");
            // Find the parent element and append
            const detailStatus = document.querySelector('.detail-status');
            if (detailStatus) {
                statusBadge.id = 'kyb-detail-status-badge';
                detailStatus.appendChild(statusBadge);
            }
        }
        
        if (response.results.overall_status) {
            const resultBadge = createResultBadge(response.results.overall_status);
            const resultBadgeElement = document.getElementById('kyb-detail-result-badge');
            if (resultBadgeElement) {
                resultBadgeElement.replaceWith(resultBadge);
                resultBadge.id = 'kyb-detail-result-badge';
            } else {
                console.warn("Element 'kyb-detail-result-badge' not found");
                // Find the parent element and append
                const detailStatus = document.querySelector('.detail-status');
                if (detailStatus) {
                    resultBadge.id = 'kyb-detail-result-badge';
                    detailStatus.appendChild(resultBadge);
                }
            }
        }
        
        // Summary
        document.getElementById('kyb-detail-summary').textContent = response.results.summary || 'No summary available';
        
        // Group checks by agent type
        const checksByAgent = {};
        response.results.verification_checks.forEach(check => {
            if (!checksByAgent[check.agent_type]) {
                checksByAgent[check.agent_type] = [];
            }
            checksByAgent[check.agent_type].push(check);
        });
        
        // Clear existing checks
        document.getElementById('kyb-normal-diligence-checks').innerHTML = '';
        document.getElementById('kyb-irs-match-checks').innerHTML = '';
        document.getElementById('kyb-sos-filings-checks').innerHTML = '';
        document.getElementById('kyb-additional-checks').innerHTML = '';
        
        // Populate normal diligence checks
        const normalDiligenceChecks = checksByAgent['NormalDiligenceAgent'] || [];
        normalDiligenceChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('kyb-normal-diligence-checks').appendChild(checkItem);
        });
        
        // Populate IRS match checks
        const irsMatchChecks = checksByAgent['IrsMatchAgent'] || [];
        irsMatchChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('kyb-irs-match-checks').appendChild(checkItem);
        });
        
        // Populate SOS filings checks
        const sosFilingsChecks = checksByAgent['SosFilingsAgent'] || [];
        sosFilingsChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('kyb-sos-filings-checks').appendChild(checkItem);
        });
        
        // Populate additional checks
        const additionalCheckAgents = ['EinLetterAgent', 'ArticlesIncorporationAgent'];
        
        const additionalChecks = [];
        additionalCheckAgents.forEach(agent => {
            if (checksByAgent[agent]) {
                additionalChecks.push(...checksByAgent[agent]);
            }
        });
        
        additionalChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('kyb-additional-checks').appendChild(checkItem);
        });
        
        // Populate UBO list
        document.getElementById('kyb-ubo-list').innerHTML = '';
        if (response.results.ubo_reports && response.results.ubo_reports.length > 0) {
            response.results.ubo_reports.forEach(ubo => {
                const uboItem = document.createElement('div');
                uboItem.classList.add('ubo-item');
                
                uboItem.innerHTML = `
                    <div class="ubo-header">
                        <div class="ubo-title">UBO: ${ubo.user_id}</div>
                        <div class="ubo-status">
                            ${createStatusBadge(ubo.status).outerHTML}
                            ${ubo.result ? createResultBadge(ubo.result).outerHTML : ''}
                        </div>
                    </div>
                    <div class="ubo-info">
                        <div class="ubo-info-item">
                            <label>Verification ID:</label>
                            <span>${ubo.verification_id}</span>
                        </div>
                    </div>
                    <div class="ubo-action">
                        <button class="ubo-view-btn">View Details</button>
                    </div>
                `;
                
                // Add click handler for viewing UBO details
                uboItem.querySelector('.ubo-view-btn').addEventListener('click', () => {
                    currentUboVerificationId = ubo.verification_id;
                    parentBusinessVerificationId = response.verification_id;
                    loadUboDetails(ubo.verification_id);
                });
                
                document.getElementById('kyb-ubo-list').appendChild(uboItem);
            });
        } else {
            document.getElementById('kyb-ubo-list').innerHTML = '<p>No UBO verifications found</p>';
        }
        
        // Show the page
        showPage('kybDetail');
    } catch (error) {
        console.error('Error loading KYB details:', error);
        showToast('Error loading verification details', 'error');
    }
}

// UBO Details
async function loadUboDetails(verificationId) {
    try {
        const response = await fetchApi(`/verify/report/detail/${verificationId}`);
        
        if (!response) return;
        
        // Update header info
        document.getElementById('ubo-detail-id').textContent = response.verification_id;
        document.getElementById('ubo-detail-user-id').textContent = response.verification_id.split('-')[0] || 'N/A';
        document.getElementById('ubo-detail-created').textContent = formatDate(response.created_at);
        document.getElementById('ubo-detail-completed').textContent = formatDate(response.completed_at);
        
        // Status and result badges - fix the null element issue
        const statusBadge = createStatusBadge(response.status);
        const statusBadgeElement = document.getElementById('ubo-detail-status-badge');
        if (statusBadgeElement) {
            statusBadgeElement.replaceWith(statusBadge);
            statusBadge.id = 'ubo-detail-status-badge';
        } else {
            console.warn("Element 'ubo-detail-status-badge' not found");
            // Find the parent element and append
            const detailStatus = document.querySelector('.detail-status');
            if (detailStatus) {
                statusBadge.id = 'ubo-detail-status-badge';
                detailStatus.appendChild(statusBadge);
            }
        }
        
        if (response.results.overall_status) {
            const resultBadge = createResultBadge(response.results.overall_status);
            const resultBadgeElement = document.getElementById('ubo-detail-result-badge');
            if (resultBadgeElement) {
                resultBadgeElement.replaceWith(resultBadge);
                resultBadge.id = 'ubo-detail-result-badge';
            } else {
                console.warn("Element 'ubo-detail-result-badge' not found");
                // Find the parent element and append
                const detailStatus = document.querySelector('.detail-status');
                if (detailStatus) {
                    resultBadge.id = 'ubo-detail-result-badge';
                    detailStatus.appendChild(resultBadge);
                }
            }
        }
        
        // Summary
        document.getElementById('ubo-detail-summary').textContent = response.results.summary || 'No summary available';
        
        // Group checks by agent type
        const checksByAgent = {};
        response.results.verification_checks.forEach(check => {
            if (!checksByAgent[check.agent_type]) {
                checksByAgent[check.agent_type] = [];
            }
            checksByAgent[check.agent_type].push(check);
        });
        
        // Clear existing checks
        document.getElementById('ubo-initial-diligence-checks').innerHTML = '';
        document.getElementById('ubo-gov-id-checks').innerHTML = '';
        document.getElementById('ubo-additional-checks').innerHTML = '';
        
        // Populate initial diligence checks
        const initialDiligenceChecks = checksByAgent['InitialDiligenceAgent'] || [];
        initialDiligenceChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('ubo-initial-diligence-checks').appendChild(checkItem);
        });
        
        // Populate gov id checks
        const govIdChecks = [
            ...(checksByAgent['GovtIdVerificationAgent'] || []),
            ...(checksByAgent['IdSelfieVerificationAgent'] || []),
            ...(checksByAgent['IdCheckAgent'] || [])
        ];
        govIdChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('ubo-gov-id-checks').appendChild(checkItem);
        });
        
        // Populate additional checks
        const additionalCheckAgents = ['AamvaVerificationAgent', 'EmailPhoneIpVerificationAgent', 
                                      'PaymentBehaviorAgent', 'LoginActivitiesAgent',
                                      'SiftVerificationAgent', 'OfacVerificationAgent'];
        
        const additionalChecks = [];
        additionalCheckAgents.forEach(agent => {
            if (checksByAgent[agent]) {
                additionalChecks.push(...checksByAgent[agent]);
            }
        });
        
        additionalChecks.forEach(check => {
            const checkItem = createCheckItem(check);
            document.getElementById('ubo-additional-checks').appendChild(checkItem);
        });
        
        // Show the page
        showPage('uboDetail');
    } catch (error) {
        console.error('Error loading UBO details:', error);
        showToast('Error loading UBO verification details', 'error');
    }
}

function createCheckItem(check) {
    const checkItem = document.createElement('div');
    checkItem.classList.add('check-item');
    
    const statusIcons = {
        'passed': 'fas fa-check-circle',
        'failed': 'fas fa-times-circle',
        'warning': 'fas fa-exclamation-triangle'
    };
    
    const iconClass = statusIcons[check.status.toLowerCase()] || 'fas fa-question-circle';
    
    checkItem.innerHTML = `
        <div class="check-icon ${check.status.toLowerCase()}">
            <i class="${iconClass}"></i>
        </div>
        <div class="check-content">
            <div class="check-name">${check.check_name}</div>
            <div class="check-details">${check.details || ''}</div>
        </div>
    `;
    
    return checkItem;
}

// New verification form handling
document.getElementById('new-kyc').addEventListener('click', function() {
    document.getElementById('new-kyc-form-container').classList.remove('hidden');
    document.getElementById('new-kyb-form-container').classList.add('hidden');
});

document.getElementById('new-kyb').addEventListener('click', function() {
    document.getElementById('new-kyb-form-container').classList.remove('hidden');
    document.getElementById('new-kyc-form-container').classList.add('hidden');
});

document.getElementById('cancel-kyc').addEventListener('click', function() {
    document.getElementById('new-kyc-form-container').classList.add('hidden');
});

document.getElementById('cancel-kyb').addEventListener('click', function() {
    document.getElementById('new-kyb-form-container').classList.add('hidden');
});

document.getElementById('new-kyc-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const userId = document.getElementById('kyc-user-id').value;
    let additionalData = {};
    
    try {
        const additionalDataText = document.getElementById('kyc-additional-data').value;
        if (additionalDataText) {
            additionalData = JSON.parse(additionalDataText);
        }
    } catch (error) {
        showToast('Invalid JSON in additional data', 'error');
        return;
    }
    
    try {
        const response = await fetchApi('/verify/kyc', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                additional_data: additionalData
            })
        });
        
        if (response) {
            showToast('KYC verification started successfully', 'success');
            document.getElementById('new-kyc-form').reset();
            document.getElementById('new-kyc-form-container').classList.add('hidden');
            
            // Navigate to KYC list
            showPage('kycList');
            loadKycList();
        }
    } catch (error) {
        console.error('Error starting KYC verification:', error);
        showToast('Error starting verification', 'error');
    }
});

document.getElementById('new-kyb-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const businessId = document.getElementById('kyb-business-id').value;
    let additionalData = {};
    
    try {
        const additionalDataText = document.getElementById('kyb-additional-data').value;
        if (additionalDataText) {
            additionalData = JSON.parse(additionalDataText);
        }
    } catch (error) {
        showToast('Invalid JSON in additional data', 'error');
        return;
    }
    
    try {
        const response = await fetchApi('/verify/business', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                business_id: businessId,
                additional_data: additionalData
            })
        });
        
        if (response) {
            showToast('KYB verification started successfully', 'success');
            document.getElementById('new-kyb-form').reset();
            document.getElementById('new-kyb-form-container').classList.add('hidden');
            
            // Navigate to KYB list
            showPage('kybList');
            loadKybList();
        }
    } catch (error) {
        console.error('Error starting KYB verification:', error);
        showToast('Error starting verification', 'error');
    }
});

// KYC filter and search
document.getElementById('kyc-status-filter').addEventListener('change', loadKycList);
document.getElementById('kyc-search-btn').addEventListener('click', loadKycList);
document.getElementById('kyc-search').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        loadKycList();
    }
});

// KYB filter and search
document.getElementById('kyb-status-filter').addEventListener('change', loadKybList);
document.getElementById('kyb-search-btn').addEventListener('click', loadKybList);
document.getElementById('kyb-search').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        loadKybList();
    }
});

// KYC pagination
document.getElementById('kyc-prev-page').addEventListener('click', function() {
    if (currentKycPage > 1) {
        currentKycPage--;
        loadKycList();
    }
});

document.getElementById('kyc-next-page').addEventListener('click', function() {
    currentKycPage++;
    loadKycList();
});

// KYB pagination
document.getElementById('kyb-prev-page').addEventListener('click', function() {
    if (currentKybPage > 1) {
        currentKybPage--;
        loadKybList();
    }
});

document.getElementById('kyb-next-page').addEventListener('click', function() {
    currentKybPage++;
    loadKybList();
});

// Back buttons
document.getElementById('back-to-kyc-list').addEventListener('click', function() {
    showPage('kycList');
});

document.getElementById('back-to-kyb-list').addEventListener('click', function() {
    showPage('kybList');
});

document.getElementById('back-to-kyb-detail').addEventListener('click', function() {
    loadKybDetails(parentBusinessVerificationId);
});

// Sidebar navigation
document.querySelectorAll('.sidebar-item').forEach(item => {
    item.addEventListener('click', function() {
        const pageId = this.dataset.page;
        showPage(pageId);
        
        // Load page-specific data
        if (pageId === 'dashboard') {
            loadDashboardData();
        } else if (pageId === 'kycList') {
            loadKycList();
        } else if (pageId === 'kybList') {
            loadKybList();
        }
    });
});

// Init app
window.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in
    if (authToken) {
        // Try to get user info to validate token
        fetchApi('/auth/me')
            .then(userInfo => {
                if (userInfo) {
                    currentUser = userInfo;
                    document.getElementById('user-email').textContent = userInfo.email;
                    showDashboard();
                } else {
                    clearAuthToken();
                    showLoginPage();
                }
            })
            .catch(() => {
                clearAuthToken();
                showLoginPage();
            });
    } else {
        showLoginPage();
    }
});