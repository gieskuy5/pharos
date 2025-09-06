# bot.py
import os
import time

# Modul lokal (pastikan file ini ada di folder yang sama)
import mintnft
import faucet

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except Exception:
    class _Dummy:
        def __getattr__(self, k): return ""
    Fore = Style = _Dummy()

BOX_WIDTH = 90  # lebar kotak menu

def hr(char="─", width=BOX_WIDTH):
    return char * width

def draw_header():
    # Header ASCII + byline
    ascii_text = f"""{Fore.CYAN}
   ___  __ _____   ___  ____  ____  
  / _ \/ // / _ | / _ \/ __ \/ __/  
 / ___/ _  / __ |/ , _/ /_/ /\ \    
/_/  /_//_/_/ |_/_/|_|\____/___/    {Style.RESET_ALL}{Fore.YELLOW}BY GIEMDFK{Style.RESET_ALL}
"""
    print(ascii_text)

    # Kotak judul & garis atas
    print(f"{Fore.GREEN}┌{hr('─') }┐{Style.RESET_ALL}")
    title = " ✨  AVAILABLE PROJECTS  ✨ "
    pad_left = (BOX_WIDTH - len(title)) // 2
    pad_right = BOX_WIDTH - len(title) - pad_left
    print(f"{Fore.GREEN}│{Style.RESET_ALL}{' ' * pad_left}{Fore.WHITE}{title}{Style.RESET_ALL}{' ' * pad_right}{Fore.GREEN}│{Style.RESET_ALL}")
    print(f"{Fore.GREEN}├{hr('─') }┤{Style.RESET_ALL}")

def draw_menu():
    # Baris menu (teks & jarak diset agar sejajar)
    line1 = f"{Fore.GREEN}│{Style.RESET_ALL}  📦  1.  {Fore.WHITE}Mint NFTs (claim all missing){Style.RESET_ALL}{' ' * 25}{Fore.CYAN}[READY]{Style.RESET_ALL}  {Fore.GREEN}│{Style.RESET_ALL}"
    line2 = f"{Fore.GREEN}│{Style.RESET_ALL}  💧  2.  {Fore.WHITE}Faucet — run once (all wallets){Style.RESET_ALL}{' ' * 20}{Fore.CYAN}[READY]{Style.RESET_ALL}  {Fore.GREEN}│{Style.RESET_ALL}"
    line3 = f"{Fore.GREEN}│{Style.RESET_ALL}  💧  3.  {Fore.WHITE}Run All Menu{Style.RESET_ALL}{' ' * 46}{Fore.CYAN}[READY]{Style.RESET_ALL}  {Fore.GREEN}│{Style.RESET_ALL}"
    line4 = f"{Fore.GREEN}│{Style.RESET_ALL}  ✖  0.  {Fore.WHITE}Exit Program{Style.RESET_ALL}{' ' * 57}{Fore.GREEN}│{Style.RESET_ALL}"

    print(line1)
    print(line2)
    print(line3)
    print(line4)

    # Garis bawah kotak
    print(f"{Fore.GREEN}└{hr('─') }┘{Style.RESET_ALL}\n")

def ask_int(prompt: str, default=None) -> int:
    while True:
        s = input(prompt).strip()
        if s == "" and default is not None:
            return default
        if s.lstrip("-").isdigit():
            return int(s)
        print(f"{Fore.YELLOW}Masukan angka yang valid.{Style.RESET_ALL}")

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        draw_header()
        draw_menu()

        choice = ask_int(f"{Fore.LIGHTRED_EX}🎯 Select project: {Style.RESET_ALL}")

        if choice == 1:
            # Mint NFTs (claim all missing)
            try:
                delay = ask_int("Delay antar-wallet (detik, default 5): ", default=5)
                mintnft.main(delay_between_wallets_sec=delay)
            except KeyboardInterrupt:
                print("\n⚠️ Dihentikan oleh user.")
        elif choice == 2:
            # Faucet run once (all wallets)
            try:
                faucet.main(loop=False)
            except KeyboardInterrupt:
                print("\n⚠️ Dihentikan oleh user.")
        elif choice == 3:
            # Run All Menu: mint → faucet
            try:
                delay = ask_int("Delay antar-wallet (detik, default 5): ", default=5)
                mintnft.main(delay_between_wallets_sec=delay)
                faucet.main(loop=False)
            except KeyboardInterrupt:
                print("\n⚠️ Dihentikan oleh user.")
        elif choice == 0:
            print(f"{Fore.CYAN}Sampai jumpa!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.YELLOW}Pilihan tidak tersedia.{Style.RESET_ALL}")

        input(f"\n{Fore.BLUE}Tekan Enter untuk kembali ke menu…{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
