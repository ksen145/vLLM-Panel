let currentPage = 'home';
let autoRefreshInterval = null;
let isServerRunning = false;

function navigate(page) {
    document.querySelectorAll('.page-section').forEach(el => el.classList.add('d-none'));
    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.classList.remove('d-none');
    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
    const activeLink = document.querySelector(`[data-page="${page}"]`);
    if (activeLink) activeLink.classList.add('active');
    currentPage = page;
    switch(page) {
        case 'home': loadHomeInfo(); break;
        case 'server': loadServerPage(); break;
        case 'chat': loadChatPage(); break;
        case 'local': loadLocalModels(); break;
        case 'search': loadSearchPage(); break;
        case 'status': refreshMetrics(); startAutoRefresh(); break;
    }
    const nc = document.getElementById('navbarNav');
    if (nc.classList.contains('show')) new bootstrap.Collapse(nc).hide();
}

function showToast(title, message, type = 'info') {
    const toast = new bootstrap.Toast(document.getElementById('toast'));
    document.getElementById('toast-title').textContent = title;
    document.getElementById('toast-body').textContent = message;
    const iconEl = document.getElementById('toast-icon');
    iconEl.className = 'bi me-2';
    switch(type) {
        case 'success': iconEl.classList.add('bi-check-circle-fill', 'text-success'); break;
        case 'error': iconEl.classList.add('bi-x-circle-fill', 'text-danger'); break;
        case 'warning': iconEl.classList.add('bi-exclamation-triangle-fill', 'text-warning'); break;
        default: iconEl.classList.add('bi-info-circle-fill', 'text-primary');
    }
    toast.show();
}

function showConfirm(title, message, onConfirm) {
    document.getElementById('confirm-modal-body').innerHTML = `<h5>${title}</h5><p>${message}</p>`;
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    document.getElementById('confirm-btn').onclick = () => { modal.hide(); onConfirm(); };
    modal.show();
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024; const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatUptime(s) {
    if (!s) return '-';
    const h = Math.floor(s / 3600); const m = Math.floor((s % 3600) / 60); const sec = Math.floor(s % 60);
    if (h > 0) return `${h}h ${m}m ${sec}s`;
    if (m > 0) return `${m}m ${sec}s`;
    return `${sec}s`;
}

function formatDuration(s) {
    if (!s) return '-';
    const m = Math.floor(s / 60); const sec = Math.floor(s % 60);
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}

async function apiGet(url) {
    const r = await fetch(url);
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Server error'); }
    return await r.json();
}

async function apiPost(url, data = null) {
    const opts = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: data ? JSON.stringify(data) : null };
    const r = await fetch(url, opts);
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Server error'); }
    return await r.json();
}

async function apiDelete(url) {
    const r = await fetch(url, { method: 'DELETE' });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Server error'); }
    return await r.json();
}

async function loadHomeInfo() {
    try {
        const info = await apiGet('/api/info');
        const alertEl = document.getElementById('platform-alert');
        const vllmUrlEl = document.getElementById('home-vllm-url');
        const agentUrlEl = document.getElementById('home-agent-url');
        const docsEl = document.getElementById('home-vllm-docs');

        if (info.vllm_available) {
            alertEl.className = 'alert alert-success';
            alertEl.innerHTML = `<i class="bi bi-check-circle me-2"></i><strong>${info.platform_name}</strong> - vLLM available`;
        } else {
            alertEl.className = 'alert alert-warning';
            const cmd = info.platform === 'darwin' ? 'pip install vllm-mlx' : 'pip install vllm';
            alertEl.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i><strong>${info.platform_name}</strong> - vLLM not installed. Run: <code>${cmd}</code>`;
        }

        updateServerBadge(info.server.is_running);
        isServerRunning = info.server.is_running;

        const vllmUrl = `http://localhost:${info.vllm_port}/v1`;
        const docsUrl = `http://localhost:${info.vllm_port}/docs`;
        vllmUrlEl.textContent = vllmUrl;
        agentUrlEl.textContent = `base_url="${vllmUrl}"`;
        docsEl.innerHTML = info.server.is_running ? `<a href="${docsUrl}" target="_blank">OpenAPI Docs</a>` : '(start server to access)';
    } catch (e) { console.error(e); }
}

function updateServerBadge(running) {
    const badge = document.getElementById('server-status-badge');
    if (running) {
        badge.className = 'badge badge-running';
        badge.innerHTML = '<i class="bi bi-check-circle me-1"></i>Online';
    } else {
        badge.className = 'badge badge-stopped';
        badge.innerHTML = '<i class="bi bi-circle me-1"></i>Offline';
    }
}

async function loadServerPage() {
    try {
        const status = await apiGet('/api/server/status');
        updateServerPage(status);
        loadLogs();
    } catch (e) { console.error(e); }
}

function updateServerPage(status) {
    isServerRunning = status.is_running;
    updateServerBadge(status.is_running);

    const runningAlert = document.getElementById('server-running-alert');
    const stoppedAlert = document.getElementById('server-stopped-alert');
    const startBtn = document.getElementById('srv-start-btn');
    const stopBtn = document.getElementById('srv-stop-btn');

    if (status.is_running) {
        runningAlert.style.display = 'block';
        stoppedAlert.style.display = 'none';
        startBtn.style.display = 'none';
        stopBtn.style.display = 'block';
        document.getElementById('server-current-model').textContent = status.model;
        document.getElementById('server-api-link').textContent = status.api_url;
        document.getElementById('server-api-link').href = status.api_url;
        document.getElementById('server-docs-link').href = status.api_url.replace('/v1', '/docs');
    } else {
        runningAlert.style.display = 'none';
        stoppedAlert.style.display = 'block';
        startBtn.style.display = 'block';
        stopBtn.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const gpuSlider = document.getElementById('srv-gpu-mem');
    const gpuVal = document.getElementById('srv-gpu-mem-val');
    if (gpuSlider && gpuVal) gpuSlider.addEventListener('input', (e) => { gpuVal.textContent = parseFloat(e.target.value).toFixed(2); });

    const tempSlider = document.getElementById('chat-temp');
    const tempVal = document.getElementById('chat-temp-val');
    if (tempSlider && tempVal) tempSlider.addEventListener('input', (e) => { tempVal.textContent = parseFloat(e.target.value).toFixed(2); });

    const topPSlider = document.getElementById('chat-top-p');
    const topPVal = document.getElementById('chat-top-p-val');
    if (topPSlider && topPVal) topPSlider.addEventListener('input', (e) => { topPVal.textContent = parseFloat(e.target.value).toFixed(2); });

    const toolsCheck = document.getElementById('chat-enable-tools');
    const toolsConfig = document.getElementById('chat-tools-config');
    if (toolsCheck && toolsConfig) {
        toolsCheck.addEventListener('change', () => { toolsConfig.style.display = toolsCheck.checked ? 'block' : 'none'; });
    }

    const form = document.getElementById('server-form');
    if (form) {
        form.addEventListener('submit', async (e) => { e.preventDefault(); await startServer(); });
    }

    navigate('home');

    // Restore any downloads that were in progress before page reload
    restoreDownloads();

    const autoCheck = document.getElementById('auto-refresh');
    if (autoCheck) {
        autoCheck.addEventListener('change', () => { if (autoCheck.checked) startAutoRefresh(); else stopAutoRefresh(); });
    }
});

async function startServer() {
    const btn = document.getElementById('srv-start-btn');
    const logDiv = document.getElementById('server-log');

    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Starting...';
        logDiv.innerHTML = '<div class="text-info">Launching vLLM server...</div>';

        const data = {
            model: document.getElementById('srv-model').value,
            max_model_len: parseInt(document.getElementById('srv-max-len').value),
            gpu_memory_utilization: parseFloat(document.getElementById('srv-gpu-mem').value),
            tensor_parallel_size: parseInt(document.getElementById('srv-tensor').value),
            dtype: document.getElementById('srv-dtype').value,
            quantization: document.getElementById('srv-quant').value || null,
            trust_remote_code: document.getElementById('srv-trust').checked,
            enable_prefix_caching: document.getElementById('srv-prefix-cache').checked
        };

        if (!data.model) {
            showToast('Error', 'Enter a model name', 'error');
            logDiv.innerHTML += '<div class="text-danger">Error: no model specified</div>';
            return;
        }

        logDiv.innerHTML += `<div class="text-warning">Model: ${data.model}</div>`;
        logDiv.innerHTML += '<div class="text-info">Starting vLLM OpenAI server...</div>';

        const result = await apiPost('/api/server/start', data);
        updateServerPage(result);
        showToast('Success', `vLLM started with ${data.model}`, 'success');

    } catch (e) {
        logDiv.innerHTML += `<div class="text-danger">Error: ${e.message}</div>`;
        showToast('Error', e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Start Server';
    }
}

async function stopServer() {
    showConfirm('Stop vLLM Server', 'This will terminate all running requests.', async () => {
        try {
            await apiPost('/api/server/stop');
            isServerRunning = false;
            updateServerBadge(false);
            const runningAlert = document.getElementById('server-running-alert');
            const stoppedAlert = document.getElementById('server-stopped-alert');
            const startBtn = document.getElementById('srv-start-btn');
            const stopBtn = document.getElementById('srv-stop-btn');
            if (runningAlert) runningAlert.style.display = 'none';
            if (stoppedAlert) stoppedAlert.style.display = 'block';
            if (startBtn) startBtn.style.display = 'block';
            if (stopBtn) stopBtn.style.display = 'none';
            showToast('Success', 'vLLM server stopped', 'success');
        } catch (e) { showToast('Error', e.message, 'error'); }
    });
}

async function loadLogs() {
    try {
        const data = await apiGet('/api/server/logs?lines=200');
        const logDiv = document.getElementById('server-log');
        if (data.logs && data.logs.length > 0) {
            logDiv.innerHTML = data.logs.map(line => {
                let cls = '';
                if (line.includes('ERROR') || line.includes('error')) cls = 'text-danger';
                else if (line.includes('WARNING') || line.includes('warning')) cls = 'text-warning';
                else if (line.includes('INFO')) cls = 'text-info';
                return `<div class="${cls}">${escapeHtml(line)}</div>`;
            }).join('');
            logDiv.scrollTop = logDiv.scrollHeight;
        }
    } catch (e) { console.error(e); }
}

function loadChatPage() {
    const offlineAlert = document.getElementById('chat-server-offline');
    const sendBtn = document.getElementById('chat-send-btn');
    if (isServerRunning) {
        offlineAlert.style.display = 'none';
        sendBtn.disabled = false;
    } else {
        offlineAlert.style.display = 'block';
        sendBtn.disabled = true;
    }
}

async function loadSearchPage() {
    // Restore downloads view when navigating to search page
    await restoreDownloads();
}

async function sendChat() {
    if (!isServerRunning) { showToast('Error', 'Start vLLM server first', 'error'); return; }

    const resultDiv = document.getElementById('chat-result');
    const btn = document.getElementById('chat-send-btn');

    try {
        let messages;
        try { messages = JSON.parse(document.getElementById('chat-messages').value); } catch {
            showToast('Error', 'Invalid JSON in messages', 'error');
            return;
        }

        const payload = {
            messages: messages,
            max_tokens: parseInt(document.getElementById('chat-max-tokens').value),
            temperature: parseFloat(document.getElementById('chat-temp').value),
            top_p: parseFloat(document.getElementById('chat-top-p').value),
            stream: document.getElementById('chat-stream').checked
        };

        if (document.getElementById('chat-enable-tools').checked) {
            try {
                payload.tools = JSON.parse(document.getElementById('chat-tools').value);
            } catch {
                showToast('Error', 'Invalid JSON in tools', 'error');
                return;
            }
        }

        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Generating...';
        resultDiv.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="mt-3 text-muted">Waiting for response...</p></div>';

        const resp = await fetch('/api/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Request failed');
        }

        if (payload.stream) {
            let fullText = '';
            resultDiv.innerHTML = '';
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ') && line !== 'data: [DONE]') {
                        try {
                            const data = JSON.parse(line.slice(6));
                            const content = data.choices?.[0]?.delta?.content || '';
                            fullText += content;
                            resultDiv.innerHTML = `<div class="generated-text">${escapeHtml(fullText)}</div>`;
                            resultDiv.scrollTop = resultDiv.scrollHeight;
                        } catch {}
                    }
                }
            }
        } else {
            const data = await resp.json();
            const content = data.choices?.[0]?.message?.content || '';
            let html = `<div class="generated-text">${escapeHtml(content)}</div>`;

            if (data.choices?.[0]?.message?.tool_calls) {
                html += `<div class="mt-3"><strong>Tool Calls:</strong><pre style="font-size: 0.8rem; background: #f8f9fa; padding: 0.5rem; border-radius: 4px;">${JSON.stringify(data.choices[0].message.tool_calls, null, 2)}</pre></div>`;
            }

            const usage = data.usage || {};
            html += `<div class="generation-stats mt-3">
                <div class="stat-item"><div class="stat-label">Prompt Tokens</div><div class="stat-value">${usage.prompt_tokens || '-'}</div></div>
                <div class="stat-item"><div class="stat-label">Completion</div><div class="stat-value">${usage.completion_tokens || '-'}</div></div>
                <div class="stat-item"><div class="stat-label">Total</div><div class="stat-value">${usage.total_tokens || '-'}</div></div>
            </div>`;
            resultDiv.innerHTML = html;
        }

    } catch (e) {
        resultDiv.innerHTML = `<div class="text-danger">Error: ${e.message}</div>`;
        showToast('Error', e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-send me-2"></i>Send';
    }
}

function copyChatResult() {
    const text = document.querySelector('#chat-result .generated-text')?.textContent || '';
    if (text) navigator.clipboard.writeText(text).then(() => showToast('Copied', 'Text copied', 'success'));
}

function escapeHtml(t) {
    const d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML.replace(/\n/g, '<br>');
}

async function loadLocalModels() {
    try {
        // Hide files view if visible
        const filesView = document.getElementById('local-models-files');
        if (filesView) filesView.style.display = 'none';

        const data = await apiGet('/api/models/local');
        const models = data.models || [];
        document.getElementById('local-models-count').textContent = data.total_count || 0;
        document.getElementById('local-models-size').textContent = formatBytes(data.total_size || 0);
        document.getElementById('local-server-status').textContent = isServerRunning ? 'Running' : 'Stopped';

        const listEl = document.getElementById('local-models-list');
        const emptyEl = document.getElementById('local-models-empty');

        if (models.length === 0) {
            listEl.style.display = 'none';
            emptyEl.style.display = 'block';
        } else {
            listEl.style.display = 'flex';
            emptyEl.style.display = 'none';
            listEl.innerHTML = models.map(m => `
                <div class="col-md-6 col-lg-4">
                    <div class="model-card">
                        <div class="model-name"><i class="bi bi-hdd-rack me-2 text-primary"></i>${m.name}</div>
                        <div class="model-meta"><i class="bi bi-hdd me-1"></i>Size: ${formatBytes(m.size)}</div>
                        <div class="d-flex gap-2 mt-3">
                            <button class="btn btn-sm btn-success flex-grow-1" onclick="useModel('${m.name}')"><i class="bi bi-play-fill"></i> Use</button>
                            <button class="btn btn-sm btn-outline-info" onclick="showLocalModelFiles('${m.name}', '${m.path || ''}')"><i class="bi bi-folder"></i></button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteModel('${m.name}')"><i class="bi bi-trash"></i></button>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) { console.error(e); }
}

function useModel(name) {
    navigate('server');
    setTimeout(() => { document.getElementById('srv-model').value = name; }, 100);
}

async function showLocalModelFiles(name, modelPath = '') {
    const listEl = document.getElementById('local-models-list');
    const emptyEl = document.getElementById('local-models-empty');
    const listContainer = listEl.parentElement;

    // Build file list from local path
    let filesHtml = '';
    let backBtnHtml = `<button class="btn btn-outline-secondary mb-3" onclick="loadLocalModels()"><i class="bi bi-arrow-left me-1"></i>Back to Models</button>`;

    if (modelPath) {
        // Fetch file list via API
        try {
            const data = await apiGet(`/api/models/local-files/${encodeURIComponent(name)}`);
            if (data.files && data.files.length > 0) {
                filesHtml = `
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h4 class="mb-1"><i class="bi bi-folder me-2"></i>${data.model}</h4>
                            <span class="text-muted">${data.count} files</span>
                        </div>
                    </div>
                    <div class="card">
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-hover mb-0">
                                    <thead class="table-light">
                                        <tr>
                                            <th>Filename</th>
                                            <th style="width: 120px;">Size</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.files.map(f => `
                                            <tr>
                                                <td class="font-monospace" style="font-size: 0.85rem;">${f.relative_path || f.filename}</td>
                                                <td>${f.size_human || '-'}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                filesHtml = `<div class="text-center text-muted py-5"><i class="bi bi-folder-x" style="font-size: 3rem;"></i><h4 class="mt-3">No files found</h4></div>`;
            }
        } catch (e) {
            filesHtml = `<div class="alert alert-danger">${e.message}</div>`;
        }
    } else {
        filesHtml = `<div class="text-center text-muted py-5"><i class="bi bi-folder-x" style="font-size: 3rem;"></i><h4 class="mt-3">Model path not available</h4></div>`;
    }

    listEl.style.display = 'none';
    emptyEl.style.display = 'none';

    // Insert files view
    let filesView = document.getElementById('local-models-files');
    if (!filesView) {
        filesView = document.createElement('div');
        filesView.id = 'local-models-files';
        listContainer.appendChild(filesView);
    }
    filesView.style.display = 'block';
    filesView.innerHTML = backBtnHtml + filesHtml;
}

async function deleteModel(name) {
    showConfirm('Delete Model', `Delete ${name} from cache?`, async () => {
        try { await apiDelete(`/api/models/${encodeURIComponent(name)}`); showToast('Success', `Deleted ${name}`, 'success'); loadLocalModels(); }
        catch (e) { showToast('Error', e.message, 'error'); }
    });
}

async function searchModels() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) { showToast('Error', 'Enter a search query', 'warning'); return; }

    const container = document.getElementById('search-results');
    const list = document.getElementById('search-results-list');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">Searching...</p></div>';
    list.style.display = 'none';

    try {
        const data = await apiGet(`/api/models/search?query=${encodeURIComponent(query)}`);
        if (data.warning) { container.innerHTML = `<div class="alert alert-warning">${data.warning}</div>`; return; }
        if (data.results.length === 0) { container.innerHTML = '<div class="text-center py-5 text-muted"><h4>No results</h4></div>'; return; }

        container.innerHTML = `<h4 class="mb-3">Found ${data.count} models</h4>`;
        list.style.display = 'flex';
        list.innerHTML = data.results.map(m => `
            <div class="col-md-6 col-lg-4">
                <div class="model-card">
                    <div class="model-name"><i class="bi bi-stars me-2 text-warning"></i>${m.id}</div>
                    <div class="model-meta"><i class="bi bi-person me-1"></i>${m.author}</div>
                    <div class="model-tags">${m.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>
                    <div class="model-meta"><i class="bi bi-download me-1"></i>${(m.downloads/1000).toFixed(1)}K <i class="bi bi-heart-fill text-danger ms-2"></i>${m.likes}</div>
                    <div class="d-flex gap-2 mt-2">
                        <a href="https://huggingface.co/${m.id}" target="_blank" class="btn btn-sm btn-outline-secondary" title="View on HuggingFace">
                            <i class="bi bi-box-arrow-up-right"></i>
                        </a>
                        <button class="btn btn-sm btn-outline-info flex-grow-1" onclick="showModelFiles('${m.id}')">
                            <i class="bi bi-folder me-1"></i>Files
                        </button>
                        <button class="btn btn-sm btn-primary flex-grow-1" onclick="downloadModel('${m.id}')">
                            <i class="bi bi-cloud-download me-1"></i>Download
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (e) { container.innerHTML = `<div class="alert alert-danger">${e.message}</div>`; }
}

async function downloadModel(name, filename = '') {
    try {
        const payload = { model_name: name };
        if (filename) payload.filename = filename;
        const result = await apiPost('/api/models/download', payload);
        const key = result.key || name;
        if (result.status === 'started') {
            showToast('Download Started', filename ? `${name}/${filename}` : `${name} is downloading`, 'info');
            checkProgress(key, name, filename);
        }
        else showToast('Info', 'Already downloading', 'warning');
    } catch (e) { showToast('Error', e.message, 'error'); }
}

async function showModelFiles(name) {
    const container = document.getElementById('search-results');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">Loading files...</p></div>';
    document.getElementById('search-results-list').style.display = 'none';

    try {
        const data = await apiGet(`/api/models/files/${encodeURIComponent(name)}`);
        if (data.error) {
            container.innerHTML = `<div class="alert alert-danger">${data.error}</div>
                <button class="btn btn-outline-secondary mt-2" onclick="searchModels()"><i class="bi bi-arrow-left me-1"></i>Back to search</button>`;
            return;
        }

        let html = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <h4 class="mb-1"><i class="bi bi-folder me-2"></i>${data.model}</h4>
                    <span class="text-muted">${data.count} files</span>
                </div>
                <div class="d-flex gap-2">
                    <a href="https://huggingface.co/${data.model}" target="_blank" class="btn btn-outline-secondary">
                        <i class="bi bi-box-arrow-up-right me-1"></i>HuggingFace
                    </a>
                    <button class="btn btn-outline-secondary" onclick="searchModels()">
                        <i class="bi bi-arrow-left me-1"></i>Back
                    </button>
                </div>
            </div>
            <div class="card">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>Filename</th>
                                    <th style="width: 120px;">Size</th>
                                    <th style="width: 120px;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        if (data.files.length === 0) {
            html += '<tr><td colspan="3" class="text-center text-muted py-4">No model files found</td></tr>';
        } else {
            for (const f of data.files) {
                html += `
                    <tr>
                        <td class="font-monospace" style="font-size: 0.85rem;">${f.filename}</td>
                        <td>${f.size_human}</td>
                        <td>
                            <button class="btn btn-sm btn-primary" onclick="downloadModel('${data.model}', '${f.filename}')">
                                <i class="bi bi-cloud-download me-1"></i>Download
                            </button>
                        </td>
                    </tr>
                `;
            }
        }

        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<div class="alert alert-danger">${e.message}</div>
            <button class="btn btn-outline-secondary mt-2" onclick="searchModels()"><i class="bi bi-arrow-left me-1"></i>Back to search</button>`;
    }
}

async function checkProgress(key, modelName = '', filename = '') {
    const container = document.getElementById('downloads-in-progress');
    const displayName = filename ? `${modelName}/${filename}` : modelName || key;
    const safeId = key.replace(/[^a-zA-Z0-9]/g, '-');

    // Save to localStorage for persistence across page reloads
    saveDownloadState(key, { model: modelName || key, filename, status: 'downloading', progress: 0 });

    const interval = setInterval(async () => {
        try {
            const p = await apiGet(`/api/models/download-progress/${encodeURIComponent(key)}`);
            if (p.status === 'not_found') {
                clearInterval(interval);
                removeDownloadState(key);
                return;
            }

            let el = document.getElementById(`dl-${safeId}`);
            if (!el) {
                el = document.createElement('div');
                el.id = `dl-${safeId}`;
                el.className = 'card mb-3';
                container.appendChild(el);
            }

            const pct = p.progress || 0;
            const isCancellable = p.status === 'downloading';
            el.innerHTML = `
                <div class="card-header d-flex justify-content-between align-items-center">
                    <span>${displayName}</span>
                    <div class="d-flex align-items-center gap-2">
                        <span id="pct-${safeId}" class="badge bg-primary">${pct.toFixed(1)}%</span>
                        ${isCancellable ? `<button class="btn btn-sm btn-outline-danger" onclick="cancelDownload('${key}', '${safeId}')"><i class="bi bi-x-circle me-1"></i>Cancel</button>` : ''}
                    </div>
                </div>
                <div class="card-body">
                    <div class="progress" style="height: 25px;">
                        <div class="progress-bar ${p.status === 'cancelled' ? 'bg-warning' : p.status === 'failed' ? 'bg-danger' : ''} ${p.status === 'completed' ? 'bg-success' : 'progress-bar-striped progress-bar-animated'}"
                             id="bar-${safeId}" style="width: ${pct}%"></div>
                    </div>
                    <div class="mt-2 small text-muted" id="det-${safeId}"></div>
                </div>
            `;

            const det = document.getElementById(`det-${safeId}`);
            if (p.status === 'completed') {
                clearInterval(interval);
                det.textContent = 'Complete!';
                showToast('Success', `${displayName} downloaded`, 'success');
                removeDownloadState(key);
                setTimeout(() => { if (el?.parentNode) el.remove(); }, 5000);
            } else if (p.status === 'failed') {
                clearInterval(interval);
                det.textContent = `Failed: ${p.error || 'Unknown error'}`;
                removeDownloadState(key);
            } else if (p.status === 'cancelled') {
                clearInterval(interval);
                det.textContent = 'Download cancelled by user';
                removeDownloadState(key);
                setTimeout(() => { if (el?.parentNode) el.remove(); }, 5000);
            } else {
                det.textContent = p.speed ? `Speed: ${formatBytes(p.speed || 0)}/s` : 'Downloading...';
                // Update localStorage
                saveDownloadState(key, { model: modelName || key, filename, status: p.status, progress: pct });
            }
        } catch (e) { console.error(e); }
    }, 2000);
}

async function cancelDownload(key, safeId = '') {
    if (!safeId) safeId = key.replace(/[^a-zA-Z0-9]/g, '-');
    showConfirm('Cancel Download', 'Stop downloading this model?', async () => {
        try {
            await apiDelete(`/api/models/download/${encodeURIComponent(key)}`);
            const el = document.getElementById(`dl-${safeId}`);
            if (el) {
                const det = document.getElementById(`det-${safeId}`);
                if (det) det.textContent = 'Cancelling...';
                const bar = document.getElementById(`bar-${safeId}`);
                if (bar) {
                    bar.className = 'progress-bar bg-warning';
                    bar.style.width = '100%';
                }
                const cancelBtn = el.querySelector('button');
                if (cancelBtn) cancelBtn.disabled = true;
            }
            showToast('Cancelled', 'Download cancelled', 'info');
        } catch (e) {
            showToast('Error', e.message, 'error');
        }
    });
}

// --- localStorage helpers for download persistence ---

const DL_STATE_KEY = 'vllm_downloads';

function getDownloadStates() {
    try {
        return JSON.parse(localStorage.getItem(DL_STATE_KEY) || '{}');
    } catch { return {}; }
}

function saveDownloadState(key, data) {
    const states = getDownloadStates();
    states[key] = { ...states[key], ...data, timestamp: Date.now() };
    localStorage.setItem(DL_STATE_KEY, JSON.stringify(states));
}

function removeDownloadState(key) {
    const states = getDownloadStates();
    delete states[key];
    localStorage.setItem(DL_STATE_KEY, JSON.stringify(states));
}

async function restoreDownloads() {
    const states = getDownloadStates();
    const keys = Object.keys(states);
    if (keys.length === 0) return;

    // Show downloads-in-progress section
    const container = document.getElementById('downloads-in-progress');
    if (container && keys.length > 0) {
        container.style.display = 'block';
    }

    // Check server for actual progress
    try {
        const serverData = await apiGet('/api/models/downloads');
        const serverDownloads = serverData.downloads || [];
        const serverKeys = new Set(serverDownloads.map(d => d.key));

        for (const key of keys) {
            const state = states[key];
            const displayName = state.filename ? `${state.model}/${state.filename}` : state.model;

            if (serverKeys.has(key)) {
                const serverEntry = serverDownloads.find(d => d.key === key);
                if (serverEntry?.status === 'cancelled') {
                    showToast('Cancelled', `${displayName} was cancelled`, 'info');
                    removeDownloadState(key);
                } else {
                    // Still active on server, resume tracking
                    checkProgress(key, state.model, state.filename || '');
                }
            } else {
                // Not on server anymore - check if it completed or was lost
                const progressResp = await apiGet(`/api/models/download-progress/${encodeURIComponent(key)}`);
                if (progressResp.status === 'completed') {
                    showToast('Completed', `${displayName} was downloaded`, 'success');
                } else if (progressResp.status === 'failed') {
                    showToast('Failed', `${displayName}: ${progressResp.error || 'Unknown error'}`, 'error');
                } else if (progressResp.status === 'cancelled') {
                    showToast('Cancelled', `${displayName} was cancelled`, 'info');
                } else {
                    // Lost track
                    showToast('Lost track', `Download status for ${displayName} is unknown`, 'warning');
                }
                removeDownloadState(key);
            }
        }
    } catch (e) { console.error('Failed to restore downloads:', e); }
}

async function refreshMetrics() {
    try {
        const status = await apiGet('/api/server/status');
        const metrics = await apiGet('/api/metrics');
        const info = await apiGet('/api/info');

        isServerRunning = status.is_running;
        updateServerBadge(status.is_running);

        document.getElementById('status-server-status').innerHTML = status.is_running ? '<span class="badge badge-running">Running</span>' : '<span class="badge badge-stopped">Stopped</span>';
        document.getElementById('status-server-model').textContent = status.model || '-';
        document.getElementById('status-server-pid').textContent = status.pid || '-';
        document.getElementById('status-server-uptime').textContent = formatUptime(status.uptime);

        const cpuPct = metrics.system.cpu_percent;
        document.getElementById('status-cpu-pct').textContent = `${cpuPct}%`;
        document.getElementById('status-cpu-bar').style.width = `${cpuPct}%`;
        document.getElementById('status-cpu-bar').className = 'progress-bar ' + (cpuPct > 80 ? 'bg-danger' : cpuPct > 50 ? 'bg-warning' : 'bg-success');
        document.getElementById('status-cpu-cores').textContent = metrics.system.cpu_count;

        const memPct = (metrics.system.memory.percent || 0).toFixed(1);
        document.getElementById('status-mem-used').textContent = formatBytes(metrics.system.memory.used || 0);
        document.getElementById('status-mem-total').textContent = formatBytes(metrics.system.memory.total || 0);
        document.getElementById('status-mem-bar').style.width = `${memPct}%`;

        const gpuCard = document.getElementById('gpu-card');
        if (metrics.gpu.available && metrics.gpu.gpus) {
            gpuCard.style.display = 'block';
            document.getElementById('gpu-info').innerHTML = metrics.gpu.gpus.map((g, i) => `
                <div class="mb-3">
                    <h6><i class="bi bi-gpu-card me-2"></i>GPU ${i}: ${g.name}</h6>
                    <div class="metric-row"><span class="metric-label">Memory</span><span class="metric-value">${(g.memory_usage_percent || 0).toFixed(1)}%</span></div>
                    <div class="progress mt-2 mb-3" style="height:20px;"><div class="progress-bar ${(g.memory_usage_percent||0) > 80 ? 'bg-danger' : (g.memory_usage_percent||0) > 60 ? 'bg-warning' : 'bg-success'}" style="width:${g.memory_usage_percent||0}%"></div></div>
                    <div class="row">
                        <div class="col-4"><div class="metric-row"><span class="metric-label">Used</span><span class="metric-value">${formatBytes(g.memory_used||0)}</span></div></div>
                        <div class="col-4"><div class="metric-row"><span class="metric-label">Free</span><span class="metric-value">${formatBytes(g.memory_free||0)}</span></div></div>
                        <div class="col-4"><div class="metric-row"><span class="metric-label">Total</span><span class="metric-value">${formatBytes(g.memory_total||0)}</span></div></div>
                    </div>
                </div>
            `).join('');
        } else { gpuCard.style.display = 'none'; }

        const vllmProcCard = document.getElementById('vllm-proc-card');
        if (metrics.vllm_process) {
            vllmProcCard.style.display = 'block';
            document.getElementById('status-vllm-cpu').textContent = `${metrics.vllm_process.cpu_percent}%`;
            document.getElementById('status-vllm-mem').textContent = formatBytes(metrics.vllm_process.memory_rss);
            document.getElementById('status-vllm-threads').textContent = metrics.vllm_process.threads;
        } else { vllmProcCard.style.display = 'none'; }
    } catch (e) { console.error(e); }
}

function startAutoRefresh() {
    stopAutoRefresh();
    const cb = document.getElementById('auto-refresh');
    if (cb?.checked) autoRefreshInterval = setInterval(refreshMetrics, 5000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) { clearInterval(autoRefreshInterval); autoRefreshInterval = null; }
}
