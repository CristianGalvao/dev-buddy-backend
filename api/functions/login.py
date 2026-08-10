from pydantic import BaseModel
from ldap3 import Server, Connection, ALL, SUBTREE
from fastapi import HTTPException, status


LDAP_SERVER = "ldap://127.0.0.1:389"
LDAP_BASE_DN = "dc=devbuddy,dc=local"
LDAP_ADMIN_DN = f"cn=admin,{LDAP_BASE_DN}"
LDAP_ADMIN_PASSWORD = "adminpassword"

class LoginRequest(BaseModel):
    uid: str
    password: str
    

def login(uid: str, password: str):
    
    user_dn = f"uid={uid},ou=users,{LDAP_BASE_DN}"
    
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        auth_conn = Connection(server, user=user_dn, password=password, auto_bind=False)
        
        if not auth_conn.bind():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail='Não Autorizado'
            )
            
        auth_conn.unbind()
                
        admin_conn = Connection(server, user=LDAP_ADMIN_DN, password=LDAP_ADMIN_PASSWORD, auto_bind=True)

        search_filter_group = "(&(objectClass=groupOfNames)(cn=g_intranet))"
        
        admin_conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=search_filter_group,
            search_scope=SUBTREE,
            attributes=['member']
        )
        
        if len(admin_conn.entries) == 0:
            admin_conn.unbind()
            raise HTTPException(status_code=403, detail="Grupo da Intranet não encontrado.")
            
        group_entry = admin_conn.entries[0]
        members = [str(m).lower() for m in group_entry.member]
        
        if user_dn.lower() not in members:
            admin_conn.unbind()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: Você não pertence ao grupo da Intranet."
            )
            
        admin_conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            search_scope=SUBTREE,
            attributes=['cn', 'mail', 'title', 'telephoneNumber']
        )
        
        user_data = {
            "uid": uid,
            "name": uid,
            "mail": "",
            "title": "",
            "phone": ""
        }
        
        if len(admin_conn.entries) > 0:
            
            entry = admin_conn.entries[0]
            raw = entry.entry_raw_attributes
            
            if 'cn' in raw and raw['cn']:
                user_data["name"] = raw['cn'][0].decode('utf-8')
            if 'mail' in raw and raw['mail']:
                user_data["mail"] = raw['mail'][0].decode('utf-8')
            if 'title' in raw and raw['title']:
                user_data["title"] = raw['title'][0].decode('utf-8')
            if 'telephoneNumber' in raw and raw['telephoneNumber']:
                user_data["phone"] = raw['telephoneNumber'][0].decode('utf-8')
                
        admin_conn.unbind()
        
        return {
            "success": True,
            "message": "Login realizado com sucesso!",
            **user_data
        }

    except HTTPException as error:
        raise error
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar dados no LDAP: {str(e)}"
        )
        
        