document.addEventListener("DOMContentLoaded", () => {
    // DOM要素の取得
    const form = document.getElementById("generator-form");
    const youtubeUrlInput = document.getElementById("youtube-url");
    const sensitivityInput = document.getElementById("sensitivity");
    const sensitivityVal = document.getElementById("sensitivity-val");
    const aiSummaryEnabled = document.getElementById("ai-summary-enabled");
    const aiSummaryState = document.getElementById("ai-summary-state");
    const toastContainer = document.getElementById("toast-container");
    
    const inputSection = document.getElementById("input-section");
    const loadingSection = document.getElementById("loading-section");
    const loadingStatus = document.getElementById("loading-status");
    const resultSection = document.getElementById("result-section");
    
    const resultTitle = document.getElementById("result-title");
    const resultSlideCount = document.getElementById("result-slide-count");
    const downloadBtn = document.getElementById("download-btn");
    const backToTopBtn = document.getElementById("back-to-top-btn");
    const saveFormatBadge = document.getElementById("save-format-badge");
    const formatPptxRadio = document.getElementById("format-pptx");
    const formatMarkdownRadio = document.getElementById("format-markdown");
    const previewContainer = document.getElementById("slides-preview-container");

    // 変化レベル（1〜10）のラベルテキスト
    const changeLevelTexts = {
        1:  "非常に敏感",
        2:  "敏感",
        3:  "やや敏感",
        4:  "やや標準",
        5:  "標準",
        6:  "やや鈍感",
        7:  "鈍感",
        8:  "やや大雑把",
        9:  "大雑把",
        10: "最も鈍感"
    };


    // レンジスライダーのリアルタイム表示制御
    sensitivityInput.addEventListener("input", (e) => {
        sensitivityVal.textContent = changeLevelTexts[e.target.value];
    });

    function syncAiSummaryState() {
        aiSummaryState.textContent = aiSummaryEnabled.checked ? "ON" : "OFF";
    }

    aiSummaryEnabled.addEventListener("change", syncAiSummaryState);
    syncAiSummaryState();

    function syncSaveFormatState() {
        if (formatPptxRadio && saveFormatBadge) {
            saveFormatBadge.textContent = formatPptxRadio.checked ? "PowerPoint" : "Markdown";
        }
    }
    if (formatPptxRadio && formatMarkdownRadio) {
        formatPptxRadio.addEventListener("change", syncSaveFormatState);
        formatMarkdownRadio.addEventListener("change", syncSaveFormatState);
        syncSaveFormatState();
    }

    // 秒数を分:秒フォーマットに変換するヘルパー関数
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    // トースト通知を表示する関数（重複防止・プログレス更新対応）
    const activeToasts = {};
    function showToast(type, title, message = "", duration = 10000, options = {}) {
        const { closeable = true, replace = false } = options;
        // 既存の同種トーストがあれば置き換える
        if (replace && activeToasts[type]) {
            const old = activeToasts[type];
            clearTimeout(old.removeTimer);
            old.toast.classList.add("exit");
            setTimeout(() => old.toast.remove(), 300);
            delete activeToasts[type];
        }
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        // アイコン設定
        const iconMap = {
            success: "check_circle",
            error: "error",
            info: "info",
            warning: "warning_amber",
            progress: "hourglass_bottom"
        };
        const icon = iconMap[type] || "info";
        const closeBtnHtml = closeable ? `<button class="toast-close" aria-label="閉じる">✖</button>` : "";
        toast.innerHTML = `
            <span class="material-icons-round toast-icon">${icon}</span>
            <div class="toast-content">
                <div class="toast-title">${escapeHtml(title)}</div>
                ${message ? `<div class="toast-message">${escapeHtml(message)}</div>` : ''}
            </div>
            <div class="toast-progress"></div>
            ${closeBtnHtml}
        `;
        // 閉じるボタンハンドラ
        if (closeable) {
            toast.querySelector(".toast-close").addEventListener("click", () => {
                clearTimeout(removeTimer);
                toast.classList.add("exit");
                setTimeout(() => toast.remove(), 300);
            });
        }
        toastContainer.appendChild(toast);
        // プログレスバーアニメーション（CSS transition）
        const progressBar = toast.querySelector(".toast-progress");
        progressBar.style.transition = `transform ${duration}ms linear`;
        progressBar.style.transform = "scaleX(1)";
        requestAnimationFrame(() => {
            progressBar.style.transform = "scaleX(0)";
        });
        // 自動削除タイマー
        const removeTimer = setTimeout(() => {
            toast.classList.add("exit");
            setTimeout(() => toast.remove(), 300);
        }, duration);
        // アクティブトーストとして記録
        activeToasts[type] = { toast, removeTimer };
        // 削除後にマップからクリア
        toast.addEventListener('transitionend', () => {
            if (activeToasts[type] && activeToasts[type].toast === toast) {
                delete activeToasts[type];
            }
        });
        return toast;
    }

    // キャンセルボタンの取得と状態変数
    const cancelBtn = document.getElementById("cancel-btn");
    let currentTaskId = null;
    let pollingInterval = null;
    let latestResultData = null;
    const sessionTaskIds = [];

    // キャンセル処理
    cancelBtn.addEventListener("click", async () => {
        if (!currentTaskId) return;
        
        cancelBtn.disabled = true;
        cancelBtn.querySelector("span:last-child").textContent = "中止しています...";
        
        try {
            const response = await fetch(`/api/cancel/${currentTaskId}`, {
                method: "POST"
            });
            if (response.ok) {
                showToast("info", "処理中止", "処理の中止をリクエストしました。");
            }
        } catch (error) {
            console.error("キャンセルエラー:", error);
        } finally {
            // ポーリング停止とUIリセット
            stopPolling();
            resetUI();
        }
    });

    function resetUI() {
        loadingSection.classList.add("hidden");
        inputSection.classList.remove("hidden");
        resultSection.classList.add("hidden");
        if (downloadBtn) downloadBtn.classList.remove("hidden");
        const downloadLabel = downloadBtn?.querySelector("span:last-child");
        if (downloadLabel) {
            downloadLabel.textContent = formatPptxRadio.checked ? "PowerPoint をダウンロード" : "Markdown 一式を保存";
        }
        latestResultData = null;
        // キャンセルボタンの活性化状態をリセット
        cancelBtn.disabled = false;
        cancelBtn.querySelector("span:last-child").textContent = "生成を中止する";
        const progressFill = document.getElementById("progress-fill");
        progressFill.classList.remove("active");
        progressFill.style.width = "30%";
        // ログコンテナもクリア
        const logContainer = document.getElementById('log-container');
        if (logContainer) logContainer.innerHTML = "";
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
        currentTaskId = null;
    }

    function logMessage(msg) {
        console.log(`> ${msg}`);
    }

    async function fetchArtifact(taskId, artifactPath) {
        const encodedPath = artifactPath
            .split("/")
            .map((segment) => encodeURIComponent(segment))
            .join("/");
        const response = await fetch(`/api/artifacts/${encodeURIComponent(taskId)}/${encodedPath}`);
        if (!response.ok) {
            throw new Error("成果物ファイルの取得に失敗しました。");
        }
        return response.blob();
    }

    async function fetchMarkdownFile(taskId, filename) {
        const response = await fetch(`/api/download/${encodeURIComponent(taskId)}/${encodeURIComponent(filename)}`);
        if (!response.ok) {
            throw new Error("Markdownファイルの取得に失敗しました。");
        }
        return response.text();
    }

    async function writeTextFile(directoryHandle, filename, content) {
        const fileHandle = await directoryHandle.getFileHandle(filename, { create: true });
        const writable = await fileHandle.createWritable();
        await writable.write(content);
        await writable.close();
    }

    async function writeBlobFile(directoryHandle, filename, blob) {
        const fileHandle = await directoryHandle.getFileHandle(filename, { create: true });
        const writable = await fileHandle.createWritable();
        await writable.write(blob);
        await writable.close();
    }

    async function saveMarkdownArtifacts(resultData) {
        if (!window.showDirectoryPicker) {
            throw new Error("このブラウザはフォルダ保存に対応していません。Chromium 系ブラウザを利用してください。");
        }

        const taskId = resultData.task_id;
        const markdownFilename = resultData.download_filename;
        const assetDirname = resultData.asset_dirname;
        const assetFilenames = resultData.asset_filenames || [];

        if (!taskId || !markdownFilename || !assetDirname) {
            throw new Error("Markdown 保存に必要な情報が不足しています。");
        }

        showToast("info", "保存先を選択してください", "選択したフォルダの直下に Markdown ファイルと画像フォルダを保存します。", 4000, { replace: true });

        const directoryHandle = await window.showDirectoryPicker({ mode: "readwrite" });
        const markdownContent = await fetchMarkdownFile(taskId, markdownFilename);
        await writeTextFile(directoryHandle, markdownFilename, markdownContent);

        const assetDirectoryHandle = await directoryHandle.getDirectoryHandle(assetDirname, { create: true });
        for (let i = 0; i < assetFilenames.length; i++) {
            const assetName = assetFilenames[i];
            const assetBlob = await fetchArtifact(taskId, `${assetDirname}/${assetName}`);
            await writeBlobFile(assetDirectoryHandle, assetName, assetBlob);
        }
    }

    downloadBtn.addEventListener("click", async (e) => {
        if (!latestResultData || latestResultData.save_format !== "markdown") {
            return;
        }

        e.preventDefault();
        try {
            await saveMarkdownArtifacts(latestResultData);
            showToast("success", "保存完了", "Markdown ファイルと画像フォルダを保存しました。", 4000, { replace: true });
        } catch (error) {
            console.error(error);
            showToast("error", "保存に失敗しました", error.message);
        }
    });

    backToTopBtn.addEventListener("click", () => {
        inputSection.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    // フォーム送信処理
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const url = youtubeUrlInput.value.trim();
        const changeLevel = parseInt(sensitivityInput.value);
        const aiSummary = aiSummaryEnabled.checked;

        if (!url) {
            showToast("error", "URLが入力されていません", "YouTubeの動画URLを入力してください");
            return;
        }
        
        showToast("info", "処理開始", `変化レベル: ${changeLevelTexts[changeLevel]} / AI要約: ${aiSummary ? "ON" : "OFF"}`);

        // UI表示の切り替え
        inputSection.classList.add("hidden");
        resultSection.classList.add("hidden");
        loadingSection.classList.remove("hidden");
        loadingStatus.textContent = "処理を開始しています...";
        
        const logContainer = document.getElementById('log-container');
        if (logContainer) logContainer.innerHTML = "";
        
        const progressFill = document.getElementById("progress-fill");
        progressFill.classList.remove("active");
        progressFill.style.width = "30%";

        cancelBtn.disabled = false;
        cancelBtn.querySelector("span:last-child").textContent = "生成を中止する";

        try {
            logMessage("YouTube動画の解析を開始しました");

            // 生成APIへのリクエスト (タスクIDを即座に受け取る)
            const response = await fetch("/api/generate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    url: url,
                    change_level: changeLevel,
                    ai_summary_enabled: aiSummary,
                    save_format: formatPptxRadio.checked ? "pptx" : "markdown"
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "プレゼンテーションの生成開始に失敗しました。");
            }

            currentTaskId = data.task_id;
            if (!sessionTaskIds.includes(currentTaskId)) {
                sessionTaskIds.push(currentTaskId);
            }
            
            // ポーリング開始
            let displayedLogCount = 0;
            progressFill.classList.add("active");
            progressFill.style.width = "0%";

            const pollTask = async () => {
                if (!currentTaskId) return;

                try {
                    const statusRes = await fetch(`/api/status/${currentTaskId}`);
                    if (!statusRes.ok) {
                        throw new Error("ステータスの取得に失敗しました。");
                    }
                    const statusData = await statusRes.json();

                    // 進捗率と詳細ステータスの更新
                    progressFill.style.width = (statusData.progress || 0) + "%";
                    loadingStatus.textContent = statusData.detail || "動画データを解析しています...";

                    // 新しいログの出力
                    const logs = statusData.logs || [];
                    if (logs.length > displayedLogCount) {
                        for (let i = displayedLogCount; i < logs.length; i++) {
                            logMessage(logs[i]);
                        }
                        displayedLogCount = logs.length;
                    }

                    // 状態に応じた処理
                    if (statusData.status === "waiting_confirm") {
                        // 一時的にポーリングを停止
                        clearInterval(pollingInterval);
                        pollingInterval = null;

                        const confirmed = confirm("スライドが100枚を超えます　中止しますか？");
                        const action = confirmed ? "abort" : "continue";

                        try {
                            const confirmRes = await fetch(`/api/confirm/${currentTaskId}/${action}`, {
                                method: "POST"
                            });
                            if (!confirmRes.ok) {
                                throw new Error("確認応答の送信に失敗しました。");
                            }

                            if (action === "abort") {
                                showToast("info", "処理中止", "処理を中止しました。");
                                resetUI();
                                currentTaskId = null;
                            } else {
                                // 継続ならポーリング再開
                                pollingInterval = setInterval(pollTask, 1000);
                            }
                        } catch (confirmErr) {
                            console.error(confirmErr);
                            showToast("error", "エラーが発生しました", confirmErr.message);
                            resetUI();
                            currentTaskId = null;
                        }
                        return;
                    }

                    if (statusData.status === "completed") {
                        stopPolling();
                        
                        const resultData = statusData.result || {};
                        latestResultData = resultData;
                        const scenes = resultData.scenes || [];
                        const scenesLength = scenes.length;
                        showToast("success", "生成完了", `${scenesLength}枚のスライドを生成しました`);

                        // 生成完了後の表示処理
                        loadingSection.classList.add("hidden");
                        resultSection.classList.remove("hidden");
                        inputSection.classList.remove("hidden");

                        // サマリー情報の更新
                        resultTitle.textContent = resultData.title || "無題";
                        resultSlideCount.textContent = `全 ${scenesLength} 枚のスライドを生成しました`;
                        
                        // ダウンロードリンクの設定
                        downloadBtn.classList.remove("hidden");
                        if (resultData.save_format === "markdown") {
                            downloadBtn.href = "#";
                            downloadBtn.removeAttribute("download");
                        } else {
                            downloadBtn.href = `/api/download/${encodeURIComponent(resultData.task_id)}/${encodeURIComponent(resultData.download_filename)}`;
                            downloadBtn.download = resultData.download_filename || (resultData.title || "presentation");
                        }
                        const downloadLabel = downloadBtn.querySelector("span:last-child");
                        if (downloadLabel) {
                            downloadLabel.textContent = resultData.download_label || "成果物をダウンロード";
                        }

                        // プレビューカードの動的生成
                        previewContainer.innerHTML = "";
                        let imageLoadCount = 0;
                        scenes.forEach((scene) => {
                            const card = document.createElement("div");
                            card.className = "slide-card";

                            const imageUrl = `/api/images/${resultData.task_id}/${scene.image_name}`;

                            card.innerHTML = `
                                <div class="slide-image-wrapper">
                                    <span class="slide-badge">Slide ${scene.id + 1}</span>
                                    <img src="${imageUrl}" alt="Slide ${scene.id + 1}" loading="lazy">
                                </div>
                                <div class="slide-content">
                                    <div class="slide-timestamp">
                                        <span class="material-icons-round" style="font-size: 1rem;">schedule</span>
                                        <span>${formatTime(scene.timestamp)}</span>
                                    </div>
                                    <div class="slide-text">${escapeHtml(scene.text)}</div>
                                </div>
                            `;
                            
                            const img = card.querySelector("img");
                            img.addEventListener("load", () => {
                                imageLoadCount++;
                                if (imageLoadCount === 1) {
                                    showToast("info", "画像読み込み中", `${imageLoadCount}/${scenesLength}枚読み込み完了`, 3000, {replace:true});
                                    logMessage(`画像 ${imageLoadCount}/${scenesLength} 読み込み完了`);
                                } else if (imageLoadCount === scenesLength) {
                                    showToast("success", "すべての画像を読み込みました", `${scenesLength}枚のプレビュー準備完了`, 3000, {replace:true});
                                    logMessage("すべての画像の読み込みが完了しました");
                                }
                            });
                            
                            previewContainer.appendChild(card);
                        });

                        // 結果画面までスムーススクロール
                        resultSection.scrollIntoView({ behavior: "smooth" });

                    } else if (statusData.status === "failed") {
                        stopPolling();
                        throw new Error(statusData.error || "プレゼンテーションの生成に失敗しました。");
                    } else if (statusData.status === "cancelled") {
                        stopPolling();
                        showToast("info", "処理中止", "処理を中止しました。");
                        resetUI();
                    }

                } catch (err) {
                    console.error(err);
                    showToast("error", "エラーが発生しました", err.message);
                    stopPolling();
                    resetUI();
                }
            };

            pollingInterval = setInterval(pollTask, 1000);

        } catch (error) {
            console.error(error);
            showToast("error", "エラーが発生しました", error.message);
            stopPolling();
            resetUI();
        }
    });

    // HTMLエスケープ処理（showToastでも利用）
    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // トースト表示（外部から呼び出し可能）
    window.showToast = showToast;

    // ブラウザ閉鎖時にセッション中のタスクデータをクリーンアップする
    window.addEventListener("beforeunload", () => {
        if (sessionTaskIds.length > 0) {
            const blob = new Blob([JSON.stringify({ task_ids: sessionTaskIds })], { type: "application/json" });
            navigator.sendBeacon("/api/cleanup-session", blob);
        }
    });
});
