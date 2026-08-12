


import asyncio

from pyrogram import Client

from config import API_ID, API_HASH
from utils.encrypt import dcs
#from crypto_ops import dcs

API_ID = 9002178
API_HASH = "a315441ae0890980db3be9d404bc3c59"
SESSION = "kGxcq2xBYjc+dQxFCAuYlwU+kqDLFnkDDTW92EhRzWX6F37DOBA1CIJQi/U4Zm37Lt7Rgt6Im0fecd3SyZILbIwvP2AFQ+F5hOHwpd0GlqxWpQubGYlNCpTGvCYwX0TcUTJiNH0T+pTbk8JWDFtx68uuBWCyIpt4Q+3mar+QHthMk4M1Ykz8KNvJzSuCXw8D19VLNj0IbzweXrh70TeUDm0C1XwmGHt24iauFypNg3TGj0upf5Vm9ZnWTssANHRdZW5o9owynRFyn2doHXNjF5f2kmm7mOzPKuSWVJueha0lOCuht3XxM0laZsuZN9CbGVRJzYJ/7pJ1uGR2EENnNE+WiANN3dlyxkhciQE/VUIMltyQ+5UEbqILLK+WdHbCHt7IjjpNikMCQ+I3zQRxv8hASHpbQNHQYGBbdyOwEv1ak6GkWlCOTuwuOqVlNp/C9ikGPoT194UONc3qcASb38ptwIzF9A/kweimCNM0BO7m8suasCheG0fniduDapuGllr54Vp7"


# ISI DENGAN HASIL session_string DARI DATABASE
ENCRYPTED_SESSION = SESSION

async def main():

    # Dekripsi session yang disimpan database
    session_string = dcs(ENCRYPTED_SESSION)

    print("Session berhasil didekripsi")
    print("Panjang session:", len(session_string))

    app = Client(
        "test",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string
    )

    async with app:

        me = await app.get_me()

        print("LOGIN:", me.id, me.username)

        chat_id = -1002254980132
        message_id = 397

        try:
            msg = await app.get_messages(
                chat_id,
                message_id
            )

            print("MESSAGE:", msg)

            if msg:
                print("TEXT:", msg.text)

        except Exception as e:
            print("GET MESSAGE ERROR:", repr(e))


asyncio.run(main())