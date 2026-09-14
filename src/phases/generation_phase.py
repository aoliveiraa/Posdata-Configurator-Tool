from src.runtime_context import RuntimeContext


def run_generation_phase(
    runtime: RuntimeContext,
) -> RuntimeContext:
    """
    Generation Phase

    Responsável por:
    - POS Generation
    - XMLRPCCLI Generation
    - WAY Generation
    - FOE Generation
    - ITONA Generation
    - COD Generation
    - StoreDB Generation

    Nesta primeira versão a implementação
    ainda será migrada gradualmente do app.py.
    """

    return runtime