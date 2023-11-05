import openai
import whisper
# ffmpegが必要！
import os
from dotenv import load_dotenv

def initialize_openai_api_key(key):
    """OpenAI APIキーを環境変数から読み込む"""
    openai.api_key = key
def generate_response(prompt, model, temperature=0.2, max_tokens=1200):
    """OpenAI APIを使用して、GPTにpromptを渡して返答を生成する"""
    print('プロンプトを送信中…')
    response = openai.ChatCompletion.create(
        model=model,
        messages=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    message = str(response['choices'][-1]['message']['content'])
    return message

def add_user_input_and_generate_response(prompt, user_input):
    prompt += [{"role": "user", "content": user_input}]
    response = generate_response(prompt,"gpt-4")
    prompt += [{"role": "assistant", "content": response}]
    return prompt, response

def whisper_stt(abspath):
    model = whisper.load_model('base')
    audio = whisper.load_audio(abspath)
    text_result = model.transcribe(audio, verbose=True, language= "ja")
    return text_result['text']


if __name__ == '__main__':
    print(os.listdir())
    print(whisper_stt(r"C:\Users\card\Documents\Umi_Neko\discord-gpt-1\speech.ogg"))