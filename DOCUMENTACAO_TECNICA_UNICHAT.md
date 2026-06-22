# UniChat — Documentação Técnica

## 1. Descrição Geral do Projeto

### Objetivo do UniChat
O UniChat é um aplicativo mobile de comunicação universitária desenvolvido em Flutter, com backend em FastAPI, criado para conectar estudantes e professores em um ambiente restrito, seguro e organizado.

### Problemas que a aplicação resolve
- Centraliza a comunicação acadêmica em um único sistema.
- Reduz a dependência de grupos informais e desorganizados.
- Restringe o acesso a usuários com e-mail institucional válido.
- Facilita conversas diretas entre membros da comunidade acadêmica.
- Permite o compartilhamento de arquivos acadêmicos com controle estrutural.

### Público-alvo
- Estudantes universitários
- Professores universitários
- Futuramente, coordenações, monitorias e setores administrativos

### Objetivo do MVP
O MVP Beta 0.1 cobre apenas o núcleo funcional do produto:
1. Login Acadêmico
2. Conversas Diretas
3. Compartilhamento de arquivos (PDF e imagens)
4. Destaque para Professores

---

## 2. Arquitetura do Sistema

### Visão geral
O sistema segue o fluxo:

**Flutter → FastAPI → MySQL**

### Responsabilidades de cada camada
- **Flutter**: interface mobile e consumo da API via HTTP.
- **FastAPI**: autenticação, regras de negócio, validação e exposição dos endpoints.
- **MySQL**: persistência relacional dos dados.

### Comunicação
- O app Flutter envia requisições **HTTP**.
- A API responde em **JSON**.
- A autenticação será feita com **JWT**.
- Arquivos enviados serão armazenados no backend e referenciados no banco por URL.

### Arquitetura em camadas
- **Router**: recebe requisições HTTP e define endpoints.
- **Service**: concentra regras de negócio.
- **Repository**: acessa o banco de dados.
- **Database**: modelos e conexão com o MySQL.

---

## 3. Modelagem dos Dados

### Entidade: `users`

**Finalidade**  
Armazenar os usuários autenticáveis do sistema.

**Atributos**
- `id`: identificador único
- `name`: nome completo
- `email`: e-mail institucional único
- `password_hash`: hash da senha
- `role`: perfil do usuário (`student` ou `professor`)
- `created_at`: data de criação

**Relacionamentos**
- Um usuário participa de vários chats.
- Um usuário envia várias mensagens.

---

### Entidade: `chats`

**Finalidade**  
Representar uma conversa privada entre dois ou mais usuários.

**Atributos**
- `id`: identificador único
- `created_at`: data de criação

**Relacionamentos**
- Um chat possui vários participantes.
- Um chat possui várias mensagens.

---

### Entidade: `chat_participants`

**Finalidade**  
Tabela associativa que relaciona usuários e chats.

**Atributos**
- `chat_id`
- `user_id`

**Relacionamentos**
- Muitos usuários podem participar de muitos chats.

---

### Entidade: `messages`

**Finalidade**  
Armazenar as mensagens enviadas dentro de um chat.

**Atributos**
- `id`: identificador único
- `chat_id`: referência ao chat
- `sender_id`: referência ao autor
- `content`: conteúdo textual
- `file_url`: URL de arquivo anexado
- `created_at`: data de envio

**Relacionamentos**
- Uma mensagem pertence a um chat.
- Uma mensagem pertence a um usuário remetente.

---

## 4. Diagrama Entidade Relacionamento (DER)

```mermaid
erDiagram
    USERS {
        BIGINT id PK
        VARCHAR name
        VARCHAR email UK
        VARCHAR password_hash
        ENUM role
        DATETIME created_at
    }

    CHATS {
        BIGINT id PK
        DATETIME created_at
    }

    CHAT_PARTICIPANTS {
        BIGINT chat_id FK
        BIGINT user_id FK
    }

    MESSAGES {
        BIGINT id PK
        BIGINT chat_id FK
        BIGINT sender_id FK
        TEXT content
        VARCHAR file_url
        DATETIME created_at
    }

    USERS ||--o{ CHAT_PARTICIPANTS : participates
    CHATS ||--o{ CHAT_PARTICIPANTS : contains
    CHATS ||--o{ MESSAGES : has
    USERS ||--o{ MESSAGES : sends
```

---

## 5. Script SQL do Banco de Dados

```sql
CREATE DATABASE IF NOT EXISTS unichat_db;

USE unichat_db;

CREATE TABLE users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'professor') NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email)
);

CREATE TABLE chats (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE TABLE chat_participants (
    chat_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (chat_id, user_id),
    CONSTRAINT fk_chat_participants_chat
        FOREIGN KEY (chat_id) REFERENCES chats(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_chat_participants_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE messages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    chat_id BIGINT UNSIGNED NOT NULL,
    sender_id BIGINT UNSIGNED NOT NULL,
    content TEXT NULL,
    file_url VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_messages_chat
        FOREIGN KEY (chat_id) REFERENCES chats(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_messages_sender
        FOREIGN KEY (sender_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);
```

---

## 6. Implementação do Banco no FastAPI

### `database/base.py`

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

### `database/connection.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
```

### `core/config.py`

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

### `users/model.py`

```python
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("student", "professor", name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    sent_messages = relationship("Message", back_populates="sender", cascade="all, delete")
    chats = relationship("Chat", secondary="chat_participants", back_populates="participants")
```

### `chats/model.py`

```python
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    participants = relationship("User", secondary="chat_participants", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
```

### `messages/model.py`

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages")
```

### `chat_participants` (modelo necessário para o relacionamento N:N)

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
```

---

## 7. Configuração do `.env`

```env
DATABASE_URL=mysql+pymysql://root:SUA_SENHA@localhost:3306/unichat_db
SECRET_KEY=coloque-uma-chave-segura-aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

## 8. Dependências do projeto

```bash
uv add fastapi
uv add uvicorn
uv add sqlalchemy
uv add pymysql
uv add pydantic-settings
uv add python-jose
uv add passlib[bcrypt]
uv add python-multipart
```

---

## 9. Boas práticas

- FastAPI moderno
- SQLAlchemy 2.0
- Pydantic v2
- Arquitetura em camadas
- Código limpo e escalável
- Preparado para expansão futura

### Evolução prevista
Esta base já permite expandir o UniChat para:
- salas de turma
- notificações
- descoberta de colegas
- mensageria em tempo real
- moderação
- auditoria
- sistemas distribuídos

---

## Estrutura recomendada do projeto

```text
unichat-api/
├── .env
├── main.py
├── core/
│   ├── config.py
│   └── security.py
├── database/
│   ├── base.py
│   └── connection.py
├── users/
│   ├── model.py
│   ├── schema.py
│   ├── repository.py
│   ├── service.py
│   └── router.py
├── chats/
│   ├── model.py
│   ├── schema.py
│   ├── repository.py
│   ├── service.py
│   └── router.py
├── messages/
│   ├── model.py
│   ├── schema.py
│   ├── repository.py
│   ├── service.py
│   └── router.py
└── uploads/
```
