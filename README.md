# Discord_bot_Report-main

## 安裝與配置

### 前置需求

*   Python 3.10 或更高版本。
*   discord.py 庫 (版本 2.4.0 或兼容版本)。
*   google-generativeai 庫 (用於 Gemini AI 功能)。

### 安裝步驟

1.  **克隆或下載專案**：
    將本專案的檔案下載到您的本地電腦。

2.  **安裝 Python 依賴庫**：
    打開終端或命令提示字元，進入專案的根目錄 (包含 `Report_setup.bat` 的目錄)，然後運行以下指令來安裝必要的庫：
    ```bash
    pip install -U discord.py==2.4.0 google-generativeai
    ```
    (如果您的 `pip` 指向 Python 2，請使用 `pip3`)

3.  **配置 `setting.json`**：
    *   找到 `Discord_bot_Report/json/setting.json` 文件。
    *   用文本編輯器打開它。
    *   填寫以下字段：
        *   `"TOKEN"`: 您的 Discord 機器人 Token。您可以從 [Discord Developer Portal](https://discord.com/developers/applications) 獲取。
        *   `"GOOGLE_API_KEY"`: 您的 Google AI (Gemini) API 金鑰。您可以從 [Google AI Studio (Makersuite)](https://makersuite.google.com/) 獲取。

    示例 `setting.json` 內容：
    ```json
    {
        "TOKEN": "YOUR_DISCORD_BOT_TOKEN_HERE",
        "GOOGLE_API_KEY": "YOUR_GOOGLE_GEMINI_API_KEY_HERE"
    }
    ```
    **注意：請妥善保管您的 Token 和 API 金鑰，不要洩露給他人。**

## 運行機器人

1.  確保您已完成上述安裝與配置步驟。
2.  雙擊運行專案根目錄下的 `Report_setup.bat` 文件。
    或者，在專案根目錄下打開終端或命令提示字元，運行：
    ```bash
    py .\Discord_bot_Report/__Report.py
    ```
3.  如果一切配置正確，您應該會在終端看到類似以下的啟動訊息：
    ```
    YYYY-MM-DD HH:MM:SS.ffffff @Report >> Report is onlineing <<
    Gemini API 已成功配置，使用模型: models/gemini-1.5-flash-latest
    Gomoku (五子棋) cog 已載入 (...)
    BlackjackCog cog 已載入 (可能在您的版本中沒有明確的 Blackjack 載入日誌)
    YYYY-MM-DD HH:MM:SS.ffffff @Report >> Report is ready <<
    ```
4.  機器人成功啟動後，會顯示在線狀態，並將活動設置為 "正在看 N/A"。

## 使用指令

所有遊戲指令均為 Discord 斜線指令。

### 五子棋 (Gomoku)

*   `/gomoku start [opponent:@User]`
    *   **功能**: 開始一局新的五子棋遊戲。
    *   **參數**:
        *   `opponent` (可選): `@` 一位伺服器中的成員作為對手進行 PvP 對戰。
        *   如果**不指定** `opponent`，則開始一局與 Gemini AI 的對戰。
    *   AI對戰時，會隨機決定誰執黑子（先手）。
    *   與玩家對戰時，發出邀請者執黑子（先手）。
    *   AI 對戰時，如果 AI 先手，它會自動下第一步。

*   `/gomoku place coordinate:<座標>`
    *   **功能**: 在當前輪到您時，在棋盤上指定位置下棋。
    *   **參數**:
        *   `coordinate`: 棋盤座標，格式為 `列字母行號` (例如 `A1`, `H8`, `O15`)。
            *   **列**: 從 `A` 到 `O`。
            *   **行**: 從 `1` 到 `15`。
            *   (注意：在與 Gemini AI 的 prompt 交互中，座標系統的描述是“行A-O, 列1-15”，請確保輸入時與此一致。)

*   `/gomoku forfeit`
    *   **功能**: 放棄當前正在進行的五子棋遊戲。您的對手將獲勝。

*   `/gomoku board`
    *   **功能**: 重新顯示當前五子棋遊戲的棋盤狀態。如果頻道中存在活躍的遊戲訊息，它可能會提供一個跳轉鏈接。

### 21點 (Blackjack)

*   `/blackjack`
    *   **功能**: 開始一局新的 21點 遊戲。
    *   玩家會收到兩張初始牌，莊家一張明牌，一張暗牌。
    *   **操作**:
        *   **加牌 (Hit)**: 點擊綠色的「加牌」按鈕，再要一張牌。
        *   **停止 (Stand)**: 點擊紅色的「停止」按鈕，不再要牌，輪到莊家行動。
    *   如果玩家點數超過 21 點（爆點），則立即輸掉遊戲。
    *   莊家會持續加牌直到點數至少為 17 點。

## 程式碼結構說明

*   **`__Report.py`**: 機器人的主入口點。負責初始化機器人、加載 Cogs、處理全局事件（如 `on_ready`, `on_command_error`）。
*   **`cmds/` 目錄**: 存放機器人的功能模組 (Cogs)。
    *   `cmds/main/gomoku.py`: 實現五子棋遊戲的核心邏輯，包括遊戲狀態管理、AI交互、指令處理。
    *   `cmds/main/blackjack.py`: 實現21點遊戲的核心邏輯。
*   **`core/classes.py`**: 定義了一個基礎的 `Cog_Extension` 類，簡化了 Cogs 的初始化。
*   **`json/setting.json`**: 存儲敏感配置信息，如機器人 Token 和 API 金鑰。

## 注意事項

*   **API 金鑰安全**: `setting.json` 文件包含了敏感信息。**切勿**將此文件或其內容提交到公開的代碼倉庫（如 GitHub 的公開庫）。建議使用 `.gitignore` 文件來忽略 `setting.json`。
*   **Gemini API 使用**: 調用 Gemini API 可能會產生費用，並受到速率限制。請查閱 Google AI 的相關文檔了解詳情。
*   **錯誤處理**: 當前程式碼包含了一些基本的錯誤處理和日誌輸出。在生產環境中，可能需要更完善的錯誤管理和日誌記錄機制。
*   **棋盤座標**: 在與 Gemini AI 的 prompt 交互中，座標系統描述為“行A-O, 列1-15”。玩家在 `/gomoku place` 輸入時也應遵循此格式（例如 `H8` 代表 H 行第 8 列）。內部程式碼會將此轉換為 0-indexed 的數組索引。

## 未來可能的改進

*   更智能的五子棋 AI（例如使用 Minimax 算法或更複雜的評估函數，而非完全依賴 LLM 的即時判斷）。
*   五子棋遊戲的悔棋、求和等功能。
*   21點遊戲的分牌、加倍等高級規則。
*   更詳細的錯誤日誌和用戶反饋。
*   將配置（如 API 金鑰）完全通過環境變量加載，而不是依賴特定路徑的 JSON 文件。

---
