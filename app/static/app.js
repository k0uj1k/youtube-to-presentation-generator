document.addEventListener("DOMContentLoaded", () => {
    // DOM要素の取得
    const form = document.getElementById("generator-form");
    const youtubeUrlInput = document.getElementById("youtube-url");
    const sensitivityInput = document.getElementById("sensitivity");
    const sensitivityVal = document.getElementById("sensitivity-val");
    const comparisonResolutionEnabled = document.getElementById("comparison-resolution-enabled");
    const comparisonResolutionState = document.getElementById("comparison-resolution-state");
    const aiSummaryEnabled = document.getElementById("ai-summary-enabled");
    const aiSummaryState = document.getElementById("ai-summary-state");
    const toastContainer = document.getElementById("toast-container");
    const submitBtn = document.getElementById("submit-btn");
    const submitBtnLabel = submitBtn.querySelector("span:last-child");
    
    const inputSection = document.getElementById("input-section");
    const resultSection = document.getElementById("result-section");
    
    const resultTitle = document.getElementById("result-title");
    const resultSlideCount = document.getElementById("result-slide-count");
    const downloadBtn = document.getElementById("download-btn");
    const previewContainer = document.getElementById("slides-preview-container");
    const exitBtn = document.getElementById("exit-btn");

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

    function syncComparisonResolutionState() {
        comparisonResolutionState.textContent = comparisonResolutionEnabled.checked ? "480x270" : "160x90";
    }

    comparisonResolutionEnabled.addEventListener("change", syncComparisonResolutionState);
    syncComparisonResolutionState();

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
        // 重なり防止のため既存トーストをすべて削除
        toastContainer.querySelectorAll('.toast').forEach(t => t.remove());
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

    function setGeneratingState(isGenerating) {
        youtubeUrlInput.disabled = isGenerating;
        sensitivityInput.disabled = isGenerating;
        comparisonResolutionEnabled.disabled = isGenerating;
        aiSummaryEnabled.disabled = isGenerating;
        submitBtn.disabled = isGenerating;
        exitBtn.disabled = isGenerating;
        submitBtnLabel.textContent = isGenerating ? "生成中..." : "プレゼンテーションを生成する";
    }

    exitBtn.addEventListener("click", async () => {
        exitBtn.disabled = true;
        showToast("progress", "終了処理中", "動画と字幕のソースキャッシュを削除しています...", 10000, { replace: true, closeable: false });

        try {
            const response = await fetch("/api/source-cache/clear", {
                method: "POST"
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.detail || "ソースキャッシュの削除に失敗しました。");
            }

            showToast("success", "終了しました", "ソースキャッシュを削除しました。", 2500, { replace: true });
            setTimeout(() => {
                window.location.replace("about:blank");
            }, 600);
        } catch (error) {
            exitBtn.disabled = false;
            showToast("error", "終了処理に失敗しました", error.message || "ソースキャッシュの削除に失敗しました。", 6000, { replace: true });
        }
    });

    // フォーム送信処理
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const url = youtubeUrlInput.value.trim();
        const changeLevel = parseInt(sensitivityInput.value);
        const comparisonResolution = comparisonResolutionEnabled.checked ? "480x270" : "160x90";
        const aiSummary = aiSummaryEnabled.checked;

        if (!url) {
            showToast("error", "URLが入力されていません", "YouTubeの動画URLを入力してください");
            return;
        }
        
        showToast("info", "処理開始", `変化レベル: ${changeLevelTexts[changeLevel]} / 比較解像度: ${comparisonResolution} / AI要約: ${aiSummary ? "ON" : "OFF"}`);
        resultSection.classList.add("hidden");
        setGeneratingState(true);

        try {
            showToast("progress", "解析中", "YouTube動画を解析しています...", 15000, {replace:true, closeable:false});

            // 生成APIへのリクエスト
            const response = await fetch("/api/generate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    url: url,
                    change_level: changeLevel,
                    comparison_resolution: comparisonResolution,
                    ai_summary_enabled: aiSummary
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "プレゼンテーションの生成に失敗しました。");
            }

            // 生成完了通知
            showToast("success", "生成完了", `${data.scenes.length}枚のスライドを生成しました`, 4000, {replace:true});


            // 生成完了後の表示処理
            resultSection.classList.remove("hidden");

            // サマリー情報の更新
            resultTitle.textContent = data.title;
            resultSlideCount.textContent = `全 ${data.scenes.length} 枚のスライドを生成しました`;
            
            // ダウンロードリンクの設定
            downloadBtn.href = `/api/download/${data.task_id}/${data.pptx_filename}`;
            downloadBtn.download = data.title + ".pptx";

            // プレビューカードの動的生成
            previewContainer.innerHTML = "";
            let imageLoadCount = 0;
            data.scenes.forEach((scene) => {
                const card = document.createElement("div");
                card.className = "slide-card";

                // 画像配信用エンドポイントのURL
                const imageUrl = `/api/images/${data.task_id}/${scene.image_name}`;

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
                
                // 画像読み込み監視
                const img = card.querySelector("img");
                img.addEventListener("load", () => {
                    imageLoadCount++;
                    if (imageLoadCount === 1) {
                        showToast("info", "画像読み込み中", `${imageLoadCount}/${data.scenes.length}枚読み込み完了`, 3000, {replace:true});
                    } else if (imageLoadCount === data.scenes.length) {
                        showToast("success", "すべての画像を読み込みました", `${data.scenes.length}枚のプレビュー準備完了`, 3000, {replace:true});
                    }
                });
                
                previewContainer.appendChild(card);
            });

            // 結果画面までスムーススクロール
            resultSection.scrollIntoView({ behavior: "smooth" });

        } catch (error) {
            console.error(error);
            showToast("error", "エラーが発生しました", error.message, 6000, {replace:true});
        } finally {
            setGeneratingState(false);
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
});
