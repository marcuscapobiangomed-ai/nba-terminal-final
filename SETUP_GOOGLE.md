# Configuração Google Sheets para NBA Terminal Pro

Siga este guia para conectar sua planilha do Google ao App.

## 1. Criar Planilha
1. Crie uma nova planilha em [sheets.google.com](https://sheets.google.com).
2. Dê o nome que quiser (ex: `NBA_Bets_Database`).
3. Copie a URL da planilha, você vai precisar dela.

## 2. Ativar API no Google Cloud
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto (ex: `nba-pro-bot`).
3. No menu lateral, vá em **APIs & Services** > **Library**.
4. Pesquise e ative estas duas APIs:
   - **Google Sheets API**
   - **Google Drive API**

## 3. Criar Credenciais (Service Account)
1. Vá em **APIs & Services** > **Credentials**.
2. Clique em **+ CREATE CREDENTIALS** > **Service Account**.
3. Dê um nome (ex: `bot-user`) e clique em **Create**.
4. Pule as etapas opcionais e clique em **Done**.
5. Na lista de Service Accounts, clique no lápis (Edit) da conta que criou.
6. Vá na aba **Keys** > **Add Key** > **Create new key** > **JSON**.
7. Um arquivo `.json` será baixado no seu computador. Guarde-o!

## 4. Conectar Planilha ao Bot
1. Abra o arquivo `.json` que você baixou. Procure o campo `"client_email"`.
2. Copie esse email (algo como `bot-user@nba-pro-bot.iam.gserviceaccount.com`).
3. Volte na sua Planilha do Google.
4. Clique no botão **Compartilhar** (Share) e cole esse email. Dê permissão de **Editor**.

## 5. Configurar o App
1. Abra o arquivo `.streamlit/secrets.toml` no seu projeto (se não existir, crie a pasta e o arquivo).
2. Cole o conteúdo abaixo preenchendo com os dados do seu JSON:

```toml
[connections.gsheets]
spreadsheet = "COLE_A_URL_DA_SUA_PLANILHA_AQUI"
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "..."
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

> **Dica**: Você pode copiar todo o conteúdo do seu arquivo JSON baixado e colar dentro da seção `[connections.gsheets]`, apenas ajustando o formato para TOML se necessário, ou usar a URL pública se preferir não usar service account (menos seguro).
