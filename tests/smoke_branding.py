"""Validação nativa da identidade visual e dos cliques reais no logotipo."""

import os

from app.main import create_application
from tests.test_branding import test_all_windows_and_dialogs_inherit_application_icon, test_five_real_logo_clicks_and_interrupted_sequence, test_windows_taskbar_identity
from tests.test_branding import test_main_logo_opens_special_message, test_fast_double_clicks_and_keyboard_alternative


def main() -> None:
    test_all_windows_and_dialogs_inherit_application_icon()
    test_five_real_logo_clicks_and_interrupted_sequence()
    test_main_logo_opens_special_message()
    test_fast_double_clicks_and_keyboard_alternative()
    if os.name == "nt":
        test_windows_taskbar_identity()
    print(f"Identidade, ícones e cinco cliques validados; plataforma {create_application().platformName()}.")


if __name__ == "__main__":
    main()
