document.addEventListener("DOMContentLoaded", () => {
    // DOM要素の取得
    const form = document.getElementById("generator-form");
    const youtubeUrlInput = document.getElementById("youtube-url");
    const sensitivityInput = document.getElementById("sensitivity");
    const sensitivityVal = document.getElementById("sensitivity-val");
    
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

    // フォーム送信処理
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const url = youtubeUrlInput.value.trim();
        const minStaticDuration = 10.0; // 最小静止時間は10秒に固定
        const changeLevel = parseInt(sensitivityInput.value);

        if (!url) {
            alert("YouTubeのURLを入力してください。");
            return;
        }

        // UI表示の切り替え
        inputSection.classList.add("hidden");
        resultSection.classList.add("hidden");
        loadingSection.classList.remove("hidden");
        loadingStatus.textContent = "YouTube動画を解析しています...";

        try {
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
                previewContainer.appendChild(card);
            });

            // 結果画面までスムーススクロール
            resultSection.scrollIntoView({ behavior: "smooth" });

        } catch (error) {
            console.error(error);
            alert(`エラーが発生しました:\n${error.message}`);
            loadingSection.classList.add("hidden");
            inputSection.classList.remove("hidden");
        }
    });

    // HTMLエスケープ処理
    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
