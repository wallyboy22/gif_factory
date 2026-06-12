"""
M3 Results — Preview dos ultimos GIFs gerados.
"""

import os
import glob


def show_results(ctx, results_list=None):
    """
    Mostra preview dos GIFs gerados.

    Args:
        ctx: NotebookContext
        results_list: lista de resultados (opcional, do ultimo batch)
    """
    from IPython.display import Image as IPImage, display as ipydisplay

    output_base = ctx.config.get_output_dir()

    if results_list:
        print("## Ultimos GIFs gerados:\n")
        for i, r in enumerate(results_list):
            if r['status'] == 'success':
                gif = r.get('gif_path', '')
                if gif and os.path.exists(gif):
                    size_mb = os.path.getsize(gif) / (1024 * 1024)
                    print(f"{i + 1}. {r['product']} / {r['territory']} ({size_mb:.1f} MB)")

        print("\n## Preview dos 3 primeiros:\n")
        count = 0
        for r in results_list:
            if count >= 3:
                break
            if r['status'] == 'success' and r.get('gif_path') and os.path.exists(r['gif_path']):
                print(f"### {r['product']} — {r['territory']}")
                ipydisplay(IPImage(filename=r['gif_path']))
                count += 1
    else:
        print("Nenhum resultado ainda. Rode a Celula 3 primeiro.")
        print(f"\nProcurando GIFs existentes em {output_base}...")
        gifs = sorted(glob.glob(os.path.join(output_base, '**', '*.gif'), recursive=True))
        print(f"Encontrados: {len(gifs)} GIFs")
        for g in gifs[:5]:
            print(f"  {os.path.relpath(g, output_base)}")
