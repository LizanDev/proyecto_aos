# 🚀 Proyecto AOS
> ⚠️ **Estado:** Proyecto en proceso. Actualmente solo hay 3 facciones insertadas en la base de datos.

¡Bienvenido/a al repositorio de **Proyecto AOS**! Este proyecto es una plataforma moderna que utiliza **Python** para el backend y **Reflex** para el frontend, con integración completa a **Supabase** para autenticación y gestión de base de datos.

---

## 🛠️ Tecnologías Utilizadas

- **Backend:** Python
- **Frontend:** [Reflex](https://reflex.dev/)
- **Base de datos & Auth:** [Supabase](https://supabase.com/)
- **Gestión de variables de entorno:** Dotenv
- **Entorno virtual:** Recomendado y gestionado automáticamente

---

## ⚡ Instalación Rápida

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/tu_usuario/proyecto_aos.git
   cd proyecto_aos
   ```
2. **Crea y activa un entorno virtual:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   ```
3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configura tus variables de entorno:**
   - Crea un archivo `.env` con tus credenciales de Supabase y otras variables necesarias.

5. **Inicia el backend:**
   ```bash
   uvicorn api:app --reload
   ```
6. **Inicia el frontend:**
   ```bash
   reflex run
   ```

---

## 🌟 Características

- Autenticación segura con Supabase
- Gestión de base de datos en la nube
- Interfaz minimalista con Reflex
- Código limpio y modular
- Fácil despliegue y configuración

---

## 📁 Estructura del Proyecto

```
proyecto_aos/
├── backend/           # Lógica de negocio y API
├── frontend/          # Interfaz de usuario con Reflex
├── services/          # Servicios y utilidades
├── requirements.txt   # Dependencias
├── .env.example       # Ejemplo de variables de entorno
└── README.md          # Este archivo
```

---

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor, abre un issue o pull request para sugerencias, mejoras o reportar bugs.

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo `LICENSE` para más información.

---

<p align="center">
  <img src="assets/favicon.ico" width="80" alt="Logo Proyecto AOS" />
</p>
