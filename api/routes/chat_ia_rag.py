import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from ldap3 import Server, Connection, SUBTREE
from groq import Groq  
from dotenv import load_dotenv 
load_dotenv()

router = APIRouter()

LDAP_SERVER = "ldap://127.0.0.1:389"
LDAP_BASE_DN = "dc=devbuddy,dc=local"
LDAP_ADMIN_DN = f"cn=admin,{LDAP_BASE_DN}"
LDAP_ADMIN_PASSWORD = "adminpassword"

class ChatRequest(BaseModel):
    uid: str
    message: str
    title: Optional[str] = ""

@router.post("/api/chat")
def chat_ia_rag(data: ChatRequest):
    try:
        user_dn = f"uid={data.uid},ou=users,{LDAP_BASE_DN}"
        
        server = Server(LDAP_SERVER)
        admin_conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASSWORD, auto_bind=True)

        admin_conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=f"(&(objectClass=groupOfNames)(member={user_dn}))",
            search_scope=SUBTREE,
            attributes=['cn']
        )
        grupos = [entry.cn.value for entry in admin_conn.entries]

        admin_conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            search_scope=SUBTREE,
            attributes=['title', 'cn']
        )
        
        cargo = "Não especificado"
        if len(admin_conn.entries) > 0:
            raw = admin_conn.entries[0].entry_raw_attributes
            if 'title' in raw and raw['title']:
                cargo = raw['title'][0].decode('utf-8')

        admin_conn.unbind()

        matriz_governanca = """
        Regras de Acesso e Governança da DevBuddy:
        - Grupos disponíveis: g_intranet, g_sre_tech, g_financeiro, g_dev_backend.
        - Cargos de SRE (SRE Engineer): Devem ter acesso obrigatório a 'g_intranet' e 'g_sre_tech'.
        - Cargos de SRE NÃO podem ter acesso direto ao 'g_financeiro' por questões de compliance de SOX/Segurança, a menos que haja aprovação formal do CISO.
        """

        system_prompt = f"""
        Você é o assistente virtual de Governança e Infraestrutura da DevBuddy.
        
        Dados do Usuário Atual:
        - UID: {data.uid}
        - Cargo no LDAP: {cargo}
        - Grupos atuais no LDAP: {', '.join(grupos)}
        
        Conhecimento de Governança:
        {matriz_governanca}

        Instruções:
        - Responda à pergunta do usuário considerando o cargo dele, os grupos que ele já possui e a matriz de governança.
        - Seja direto, claro, profissional e explicativo.
        """

        api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("API_KEY_GROG")

        groq_client = Groq(api_key=api_key)
        
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data.message}
            ],
            temperature=0.3
        )

        resposta_ia = completion.choices[0].message.content

        return {
            "success": True,
            "response": resposta_ia
        }

    except Exception as e:
            import traceback
            traceback.print_exc() # <--- Isso vai imprimir o erro completo no terminal do Uvicorn
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao processar o chat com IA: {str(e)}"
            )