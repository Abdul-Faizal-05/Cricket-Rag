
document.addEventListener("DOMContentLoaded", () => {
    const queryInput = document.getElementById("query-input");
    const btnSubmit = document.getElementById("btn-submit");
    const btnExport = document.getElementById("btn-export");
    const btnRefresh = document.getElementById("btn-refresh");
    const btnQuit = document.getElementById("btn-quit");
    const connectionDot = document.getElementById("connection-dot");
    const protocolStatusText = document.getElementById("protocol-status-text");
    
    const traceSection = document.getElementById("trace-section");
    const traceLoading = document.getElementById("trace-loading");
    const traceStepsContainer = document.getElementById("trace-steps-container");
    const stepsBadge = document.getElementById("steps-badge");
    
    const answerSection = document.getElementById("answer-section");
    const finalAnswerText = document.getElementById("final-answer-text");
    const citationsPills = document.getElementById("citations-pills");
    const metaSteps = document.getElementById("meta-steps");

    const suggestionButtons = document.querySelectorAll(".suggestion-btn");

    // Quit overlay elements
    const quitOverlay = document.getElementById("quit-overlay");
    const btnConfirmQuit = document.getElementById("btn-confirm-quit");
    const btnCancelQuit = document.getElementById("btn-cancel-quit");

    let lastQueryResult = null; // Store last query response for exporting

    // Check connectivity to the FastAPI server on load
    checkBackendConnection();

    // QUIT button — show overlay
    btnQuit.addEventListener("click", () => {
        quitOverlay.classList.remove("hidden");
        lucide.createIcons();
    });

    // CANCEL quit
    btnCancelQuit.addEventListener("click", () => {
        quitOverlay.classList.add("hidden");
    });

    // CONFIRM quit — close the browser tab
    btnConfirmQuit.addEventListener("click", () => {
        window.close();
        // Fallback: if browser blocks window.close(), show a message
        setTimeout(() => {
            quitOverlay.classList.add("hidden");
            protocolStatusText.textContent = "Session terminated. You may close this tab manually.";
            connectionDot.className = "status-dot red";
        }, 300);
    });

    // Close overlay by clicking the backdrop
    quitOverlay.addEventListener("click", (e) => {
        if (e.target === quitOverlay) {
            quitOverlay.classList.add("hidden");
        }
    });

    // Hook up suggestion buttons
    suggestionButtons.forEach(button => {
        button.addEventListener("click", () => {
            const query = button.getAttribute("data-query");
            queryInput.value = query;
            queryInput.focus();
            
            // Automatically trigger the run
            runAgentQuery(query);
        });
    });

    // Submit button event
    btnSubmit.addEventListener("click", () => {
        const query = queryInput.value.trim();
        if (!query) {
            alert("Please enter a question for the IPL Analyst Agent.");
            return;
        }
        runAgentQuery(query);
    });

    // Allow Ctrl+Enter to submit
    queryInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            btnSubmit.click();
        }
    });

    // Force Refresh (resets the UI state)
    btnRefresh.addEventListener("click", () => {
        queryInput.value = "";
        traceSection.classList.add("hidden");
        answerSection.classList.add("hidden");
        traceStepsContainer.innerHTML = "";
        lastQueryResult = null;
        protocolStatusText.textContent = "Console State Cleared. Ready for Querying.";
    });

    // Export button (download JSON representation of last run)
    btnExport.addEventListener("click", () => {
        if (!lastQueryResult) {
            alert("No query intelligence to export yet. Please execute a query first.");
            return;
        }
        exportQueryData();
    });

    // Mock reconnect button click
    btnConnect.addEventListener("click", () => {
        checkBackendConnection();
    });

    // Function to check connection to backend
    async function checkBackendConnection() {
        protocolStatusText.textContent = "Verifying backend API connection...";
        try {
            // Test root endpoint or docs
            const res = await fetch("/", { method: "HEAD" });
            if (res.ok) {
                setConnectionStatus(true);
            } else {
                setConnectionStatus(false, "Server responded with status " + res.status);
            }
        } catch (err) {
            setConnectionStatus(false, err.message);
        }
    }

    function setConnectionStatus(isConnected, errorMsg = "") {
        if (isConnected) {
            connectionDot.className = "status-dot green";
            btnConnect.innerHTML = `<i data-lucide="wifi"></i> CONNECTED`;
            btnConnect.className = "brutalist-btn btn-green";
            protocolStatusText.textContent = "Dynamic Edge Agent Routing Active";
        } else {
            connectionDot.className = "status-dot red pulse";
            btnConnect.innerHTML = `<i data-lucide="wifi-off"></i> OFFLINE`;
            btnConnect.className = "brutalist-btn btn-yellow";
            protocolStatusText.textContent = `Backend Offline: ${errorMsg || "Could not reach API"}`;
        }
        lucide.createIcons();
    }

    // Run the actual API call
    async function runAgentQuery(question) {
        // Reset and show sections
        traceSection.classList.remove("hidden");
        traceLoading.classList.remove("hidden");
        traceStepsContainer.innerHTML = "";
        answerSection.classList.add("hidden");
        stepsBadge.textContent = "0 / 8 STEPS";
        
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = `<span>ANALYZING...</span> <i data-lucide="loader" class="spin"></i>`;
        lucide.createIcons();

        protocolStatusText.textContent = "Agent Routing: Running agentic reasoning loop...";

        try {
            const response = await fetch("/agent", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ question: question })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Server error (${response.status})`);
            }

            const data = await response.json();
            lastQueryResult = data;
            
            // Render the reasoning steps
            renderThinkingSteps(data.steps || []);
            
            // Render final answer
            renderFinalAnswer(data);

            protocolStatusText.textContent = "Analysis Complete. Answer Synthesized.";
        } catch (err) {
            console.error(err);
            protocolStatusText.textContent = `Error: ${err.message}`;
            
            // Show error in the terminal interface
            traceLoading.classList.add("hidden");
            traceStepsContainer.innerHTML = `
                <div class="step-card tool-unknown" style="border-left-color: red; padding: 14px; background: #220b0b;">
                    <div style="font-weight: 700; color: #ff5252; margin-bottom: 6px;">PROTOCOL INTERRUPTION ERROR</div>
                    <div style="font-family: monospace; font-size: 0.85rem; color: #ffbaba; white-space: pre-wrap;">${err.message}</div>
                </div>
            `;
        } finally {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = `<span>SUBMIT QUERY</span> <i data-lucide="send"></i>`;
            lucide.createIcons();
        }
    }

    // Render each step from the routing agent
    function renderThinkingSteps(steps) {
        traceLoading.classList.add("hidden");
        stepsBadge.textContent = `${steps.length} / 8 STEPS`;
        
        if (steps.length === 0) {
            traceStepsContainer.innerHTML = `<div style="padding: 10px; color: #888;">No tools were used. The agent answered directly.</div>`;
            return;
        }

        steps.forEach((step, idx) => {
            const stepNum = idx + 1;
            const toolClass = `tool-${step.tool}`;
            const stepCard = document.createElement("div");
            stepCard.className = `step-card ${toolClass}`;
            
            // Format input nicely based on tool
            let formattedInput = step.input;
            if (step.tool === "query_data") {
                formattedInput = formatSQL(step.input);
            }

            // Create step header
            const stepHeader = document.createElement("div");
            stepHeader.className = "step-header";
            stepHeader.innerHTML = `
                <div class="step-title-left">
                    <span class="step-badge">${step.tool}</span>
                    <span style="font-weight: 700;">STEP ${stepNum}</span>
                </div>
                <i data-lucide="chevron-down" class="step-toggle-icon"></i>
            `;

            // Create step body
            const stepBody = document.createElement("div");
            stepBody.className = "step-body";
            
            // Tool Input section
            const inputContainer = document.createElement("div");
            inputContainer.className = "code-block-container";
            inputContainer.innerHTML = `
                <div class="code-title">Tool Input:</div>
                <pre class="code-box"><code class="${step.tool === 'query_data' ? 'sql-highlight' : ''}">${escapeHtml(formattedInput)}</code></pre>
            `;
            stepBody.appendChild(inputContainer);

            // Tool Result section
            const resultContainer = document.createElement("div");
            resultContainer.className = "code-block-container";
            
            let resultDisplay = step.result;
            // If SQLite returned columns/data, let's pretty-print it as a simple table or structured text
            if (step.tool === "query_data" && step.result.includes("'columns'") && step.result.includes("'data'")) {
                resultDisplay = formatDbResult(step.result);
            }

            resultContainer.innerHTML = `
                <div class="code-title">Tool Result / Context Output:</div>
                <div class="result-box">${resultDisplay}</div>
            `;
            stepBody.appendChild(resultContainer);

            stepCard.appendChild(stepHeader);
            stepCard.appendChild(stepBody);

            // Toggle collapse functionality
            stepHeader.addEventListener("click", () => {
                stepCard.classList.toggle("collapsed");
            });

            traceStepsContainer.appendChild(stepCard);
        });

        lucide.createIcons();
    }

    // Render final output (Neural Roast Style)
    function renderFinalAnswer(data) {
        answerSection.classList.remove("hidden");
        finalAnswerText.textContent = data.final_answer || "No response synthesized.";
        
        // Render citations
        citationsPills.innerHTML = "";
        if (data.citations && data.citations.length > 0) {
            data.citations.forEach(cit => {
                const badge = document.createElement("span");
                badge.className = `citation-pill citation-${cit}`;
                
                // Display name mapping
                let dispName = cit;
                if (cit === "query_data") dispName = "⚡ SQL Database";
                if (cit === "search_docs") dispName = "📚 Season Docs";
                if (cit === "web_search") dispName = "🌐 Live Web";

                badge.textContent = dispName;
                citationsPills.appendChild(badge);
            });
        } else {
            const badge = document.createElement("span");
            badge.className = "citation-pill";
            badge.style.backgroundColor = "#ddd";
            badge.textContent = "Direct Inference";
            citationsPills.appendChild(badge);
        }

        // Render steps count
        metaSteps.textContent = `Steps: ${data.steps_used || 'N/A'}`;
    }

    // Helper to format SQLite JSON results into HTML tables
    function formatDbResult(rawString) {
        try {
            // Evaluates standard python string representation of dict: {'columns': [...], 'data': [...]}
            // Replace single quotes with double quotes for JSON parsing, but be careful with strings inside
            // Better to parse with a basic clean up or manual matching
            const cleaned = rawString.replace(/'/g, '"');
            const obj = JSON.parse(cleaned);
            
            if (obj.columns && obj.data) {
                if (obj.data.length === 0) {
                    return "[Empty Result: Query returned 0 rows]";
                }
                
                let html = '<div class="table-scroll"><table style="width:100%; border-collapse:collapse; font-size:0.75rem;">';
                // Header
                html += '<thead><tr style="background:#222; border-bottom:2px solid #444; text-align:left;">';
                obj.columns.forEach(col => {
                    html += `<th style="padding:6px; font-weight:700; color:#fff;">${col}</th>`;
                });
                html += '</tr></thead>';
                // Body
                html += '<tbody>';
                obj.data.forEach((row, i) => {
                    const bg = i % 2 === 0 ? '#181818' : '#141414';
                    html += `<tr style="background:${bg}; border-bottom:1px solid #2a2a2a;">`;
                    row.forEach(cell => {
                        html += `<td style="padding:6px; color:#a0e0ff;">${escapeHtml(String(cell))}</td>`;
                    });
                    html += '</tr>';
                });
                html += '</tbody></table></div>';
                return html;
            }
        } catch (e) {
            // Fall back to clean raw output
        }
        return escapeHtml(rawString);
    }

    // Helper to escape HTML tags to prevent XSS/broken layouts
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.innerText = text;
        return div.innerHTML;
    }

    // Helper to format SQL commands slightly for readability
    function formatSQL(sql) {
        return sql
            .replace(/\bSELECT\b/gi, 'SELECT')
            .replace(/\bFROM\b/gi, '\nFROM')
            .replace(/\bWHERE\b/gi, '\nWHERE')
            .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
            .replace(/\bORDER BY\b/gi, '\nORDER BY')
            .replace(/\bLIMIT\b/gi, '\nLIMIT')
            .replace(/\bLEFT JOIN\b/gi, '\nLEFT JOIN')
            .replace(/\bUNION\b/gi, '\nUNION\b');
    }

    // Export current run data to JSON
    function exportQueryData() {
        if (!lastQueryResult) return;
        
        const filename = `ipl_agent_intel_${Date.now()}.json`;
        const jsonStr = JSON.stringify(lastQueryResult, null, 2);
        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(jsonStr));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }
});
