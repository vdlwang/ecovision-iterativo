/**
 * Classe Usuario - Gerencia informação do usuário autenticado
 */
export class Usuario {
  id: string;
  name: string;
  email: string;
  autenticado: boolean;

  constructor(id: string, name: string, email: string, autenticado: boolean = false) {
    this.id = id;
    this.name = name;
    this.email = email;
    this.autenticado = autenticado;
  }

  to_dict(): Record<string, any> {
    return {
      id: this.id,
      name: this.name,
      email: this.email,
      autenticado: this.autenticado
    };
  }
}
