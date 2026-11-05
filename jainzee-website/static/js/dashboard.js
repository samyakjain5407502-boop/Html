const dashboardRefresh = document.getElementById('dashboard-refresh');
const dashboardSnapshot = document.getElementById('dashboard-snapshot');
const dashboardRefreshStatus = document.getElementById('dashboard-refresh-status');

dashboardRefresh.hidden = false;

async function refreshDashboard() {
    if (dashboardRefresh.disabled || document.hidden) return;
    dashboardRefresh.disabled = true;
    dashboardRefreshStatus.textContent = 'Updating…';

    try {
        const url = new URL(window.location.href);
        url.searchParams.set('snapshot', '1');
        const response = await fetch(url, { cache: 'no-store' });
        if (response.redirected || response.status === 401) {
            dashboardRefreshStatus.textContent = 'Your session expired. Reload to sign in again.';
            return;
        }
        if (!response.ok) throw new Error('Dashboard refresh failed');
        dashboardSnapshot.innerHTML = await response.text();
        dashboardRefreshStatus.textContent = 'Figures refreshed';
    } catch {
        dashboardRefreshStatus.textContent = dashboardSnapshot.querySelector('.dash-metrics')
            ? 'Refresh failed. Showing the last available figures.'
            : 'Dashboard figures are still unavailable.';
    } finally {
        dashboardRefresh.disabled = false;
    }
}

dashboardRefresh.addEventListener('click', refreshDashboard);
setInterval(refreshDashboard, 60000);
