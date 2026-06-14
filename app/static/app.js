document.addEventListener("DOMContentLoaded", () => {
    // DOM要素の取得
    const form = document.getElementById("generator-form");
    const youtubeUrlInput = document.getElementById("youtube-url");
    const sensitivityInput = document.getElementById("sensitivity");
    const sensitivityVal = document.getElementById("sensitivity-val");
    const toastContainer = document.getElementById("toast-container");
    
    const inputSection = document.getElementById("input-section");
    const loadingSection = document.getElementById("loading-section");
    const loadingStatus = document.getElementById("loading-status");
    const resultSection = document.getElementById("result-section");
    
    const resultTitle = document.getElementById("result-title");
    const resultSlideCount = document.getElementById("result-slide-count");
    const downloadBtn = document.getElementById("download-btn");
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

    // 秒数を分:秒フォーマットに変換するヘルパー関数
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    // トースト通知を表示する関数
    function showToast(type, title, message = "", duration = 10000) {
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

        toast.innerHTML = `
            <span class="material-icons-round toast-icon">${icon}</span>
            <div class="toast-content">
                <div class="toast-title">${escapeHtml(title)}</div>
                ${message ? `<div class="toast-message">${escapeHtml(message)}</div>` : ''}
            </div>
            <div class="toast-progress"></div>
        `;

        toastContainer.appendChild(toast);

        // 自動削除タイマー
        const removeTimer = setTimeout(() => {
            toast.classList.add("exit");
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, duration);

        return toast;
    }

    // フォーム送信処理
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const url = youtubeUrlInput.value.trim();
        const minStaticDuration = 10.0; // 最小静止時間は10秒に固定
        const changeLevel = parseInt(sensitivityInput.value);

        if (!url) {
            showToast("error", "URLが入力されていません", "YouTubeの動画URLを入力してください");
            return;
        }
        
        showToast("info", "処理開始", `変化レベル: ${changeLevelTexts[changeLevel]}`);


        // UI表示の切り替え
        inputSection.classList.add("hidden");
        resultSection.classList.add("hidden");
        loadingSection.classList.remove("hidden");
        loadingStatus.textContent = "YouTube動画を解析しています...";

        try {
            // 動画解析進捗
            showToast("progress", "解析中", "YouTube動画を解析しています...");
            loadingSection.classList.remove("hidden");
            loadingStatus.textContent = "YouTube動画を解析しています...";

            // 生成APIへのリクエスト
            const response = await fetch("/api/generate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    url: url,
                    min_static_duration: minStaticDuration,
                    change_level: changeLevel
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "プレゼンテーションの生成に失敗しました。");
            }

            // 生成完了通知
            showToast("success", "生成完了", `${data.scenes.length}枚のスライドを生成しました`);


            // 生成完了後の表示処理
            loadingSection.classList.add("hidden");
            resultSection.classList.remove("hidden");
            inputSection.classList.remove("hidden"); // 再度別の動画を入力できるように

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
                        showToast("info", "画像読み込み中", `${imageLoadCount}/${data.scenes.length}枚読み込み完了`, 3000);
                    } else if (imageLoadCount === data.scenes.length) {
                        showToast("success", "すべての画像を読み込みました", `${data.scenes.length}枚のプレビュー準備完了`, 3000);
                    }
                });
                
                previewContainer.appendChild(card);
            });

            // 結果画面までスムーススクロール
            resultSection.scrollIntoView({ behavior: "smooth" });

        } catch (error) {
            console.error(error);
            showToast("error", "エラーが発生しました", error.message);
            loadingSection.classList.add("hidden");
            inputSection.classList.remove("hidden");
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
