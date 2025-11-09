import { Usuario } from "./Usuario.tsx";

/**
 * Classe Autenticacao - Gerencia autenticação de usuários
 */
export class Autenticacao {
  google_client_id: string;
  private _sessions: Map<string, Record<string, any>>;

  constructor(google_client_id: string) {
    this.google_client_id = google_client_id;
    this._sessions = new Map();
  }

  loginComGoogle(tokenGoogle: string): Record<string, any> {
    console.log("Processando login com Google...");
    
    const usuario = {
      id: `user_${Date.now()}`,
      name: "Usuário Demo",
      email: "demo@ecovision.com",
      autenticado: true
    };
    
    const sessionId = `session_${Date.now()}`;
    this._sessions.set(sessionId, usuario);
    
    return { sessionId, usuario };
  }

  logout(usuario: Usuario): void {
    for (const [sessionId, sessionData] of this._sessions.entries()) {
      if (sessionData.id === usuario.id) {
        this._sessions.delete(sessionId);
        console.log(`Logout realizado para usuário ${usuario.email}`);
        return;
      }
    }
  }

  is_autenticado(email: string): boolean {
    for (const sessionData of this._sessions.values()) {
      if (sessionData.email === email && sessionData.autenticado) {
        return true;
      }
    }
    return false;
  }
}
