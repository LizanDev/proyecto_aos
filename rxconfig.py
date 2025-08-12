import reflex as rx

config = rx.Config(
    app_name="proyecto_aos",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
)