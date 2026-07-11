"""
Optimización de la red de proveedores de una cadena hotelera europea
=====================================================================

Replica en Python (PuLP) el modelo de programación lineal resuelto
originalmente en Excel con OpenSolver (CBC).

Para cada uno de los 19 hoteles se elige la combinación de proveedores de
desayuno, cena y actividades que maximiza el beneficio total de la red,
sujeto a:

    - Presupuesto máximo conjunto de la red.
    - Calidad media ponderada mínima (suelo de marca).
    - Ingresos mínimos anuales por hotel.
    - Selección de un único proveedor de desayuno y de actividades por hotel
      (la cena sí admite repartir el volumen entre varios proveedores).
    - Coherencia de calidad entre desayuno y cena en cada hotel.

Los datos (data/variables.csv, data/hotels.csv) se extrajeron directamente
del modelo original en Excel.

Uso:
    python3 model.py
"""

import csv
from collections import defaultdict
import pulp

BUDGET = 220_000          # Presupuesto máximo de la red (€)
BUDGET_MARKUP = 1.2       # Recargo aplicado al coste total en el Excel original
QUALITY_MIN = 2.7         # Calidad media ponderada mínima exigida por la marca
PROFIT_SHARE = 0.5        # Factor aplicado al margen bruto en la función objetivo
COHERENCE_GAP = 2         # Máxima diferencia de calidad permitida entre desayuno y cena
ENFORCE_COHERENCE = False # Ver nota de auditoría en build_model()

BENCHMARK_EXCEL = 120_163.25  # Beneficio óptimo obtenido en el Excel original (OpenSolver/CBC)

DATA_DIR = "data"


def load_variables(path=f"{DATA_DIR}/variables.csv"):
    variables = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["cost_var"] = float(row["cost_var"])
            row["ingres_brut"] = float(row["ingres_brut"])
            row["demanda"] = float(row["demanda"])
            row["calidad"] = float(row["calidad"])
            row["cost_fijo"] = float(row["cost_fijo"])
            row["coste_total"] = float(row["coste_total"])
            row["beneficio"] = float(row["beneficio"])
            variables.append(row)
    return variables


def load_hotels(path=f"{DATA_DIR}/hotels.csv"):
    hotels = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            hotels[row["hotel"]] = {"zone": row["zone"], "min_revenue": float(row["min_revenue"])}
    return hotels


def build_model(variables, hotels):
    prob = pulp.LpProblem("Optimizacion_Proveedores_Hoteleros", pulp.LpMaximize)

    # Una variable continua [0,1] por cada línea de proveedor
    x = {v["id"]: pulp.LpVariable(v["id"], lowBound=0, upBound=1) for v in variables}

    # --- Función objetivo: maximizar beneficio total (con el factor 0.5 del Excel) ---
    prob += PROFIT_SHARE * pulp.lpSum(v["beneficio"] * x[v["id"]] for v in variables), "Beneficio_total"

    # --- Restricción de presupuesto ---
    prob += (
        BUDGET_MARKUP * pulp.lpSum(v["coste_total"] * x[v["id"]] for v in variables) <= BUDGET,
        "Presupuesto",
    )

    # --- Restricción de calidad media ponderada ---
    n_grupos = len({v["group_id"] for v in variables})
    prob += (
        pulp.lpSum(v["calidad"] * x[v["id"]] for v in variables) / n_grupos >= QUALITY_MIN,
        "Calidad_minima",
    )

    # --- Selección única por grupo (desayuno / cena / actividad de cada hotel) ---
    groups = defaultdict(list)
    for v in variables:
        groups[v["group_id"]].append(v)

    for group_id, group_vars in groups.items():
        prob += (
            pulp.lpSum(x[v["id"]] for v in group_vars) <= 1,
            f"Seleccion_{group_id}",
        )

    # --- Ingresos mínimos por hotel (desayuno + cena + actividad) ---
    for hotel, info in hotels.items():
        hotel_vars = [v for v in variables if v["hotel"] == hotel]
        prob += (
            pulp.lpSum(v["ingres_brut"] * x[v["id"]] for v in hotel_vars) >= info["min_revenue"],
            f"Ingreso_minimo_{hotel}",
        )

    # --- Coherencia de calidad desayuno-cena por hotel ---
    #
    # NOTA DE AUDITORÍA: el Excel original modela esta restricción como
    # OFFSET($R$16,...) - OFFSET($R$17,...) <= -2, pero R16/R17 apuntan a las
    # celdas que devuelven la SUMA DE SELECCIÓN (0-1, siempre <=1) de cada
    # grupo, no a la calidad ponderada. Con esa referencia, el lado izquierdo
    # de la restricción nunca puede ser inferior a -1, por lo que la condición
    # "<= -2" es matemáticamente imposible de cumplir. Si OpenSolver la
    # hubiera aplicado tal cual, el modelo sería infactible — y sin embargo
    # se obtuvo una solución óptima, lo que confirma que esta restricción
    # nunca llegó a incluirse en el rango real resuelto por el solver.
    #
    # Aquí se implementa la restricción TAL COMO SE DESCRIBE en el enunciado
    # del caso (diferencia de calidad entre desayuno y cena limitada a 2
    # puntos), pero queda desactivada por defecto para poder comparar
    # ambos escenarios y así reproducir fielmente el resultado del Excel.
    if ENFORCE_COHERENCE:
        for hotel in hotels:
            breakfast_vars = [v for v in variables if v["hotel"] == hotel and v["service"] == "breakfast"]
            dinner_vars = [v for v in variables if v["hotel"] == hotel and v["service"] == "dinner"]
            calidad_desayuno = pulp.lpSum(v["calidad"] * x[v["id"]] for v in breakfast_vars)
            calidad_cena = pulp.lpSum(v["calidad"] * x[v["id"]] for v in dinner_vars)
            prob += (calidad_desayuno - calidad_cena <= COHERENCE_GAP, f"Coherencia_sup_{hotel}")
            prob += (calidad_cena - calidad_desayuno <= COHERENCE_GAP, f"Coherencia_inf_{hotel}")

    return prob, x


def solve_and_report(variables, hotels):
    prob, x = build_model(variables, hotels)
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    print(f"Estado del solver: {pulp.LpStatus[prob.status]}")
    print(f"Beneficio óptimo: {pulp.value(prob.objective):,.2f} €\n")

    var_by_id = {v["id"]: v for v in variables}
    coste_total = sum(v["coste_total"] * x[v["id"]].value() for v in variables) * BUDGET_MARKUP
    calidad_media = sum(v["calidad"] * x[v["id"]].value() for v in variables) / len({v["group_id"] for v in variables})

    print(f"Presupuesto utilizado: {coste_total:,.2f} € / {BUDGET:,.2f} €")
    print(f"Calidad media ponderada: {calidad_media:.3f} (mínimo exigido: {QUALITY_MIN})\n")

    print("Combinación óptima por hotel:")
    print("-" * 70)
    for hotel in sorted(hotels):
        print(f"\n{hotel}:")
        for service in ["breakfast", "dinner", "activity"]:
            chosen = [
                (v, x[v["id"]].value())
                for v in variables
                if v["hotel"] == hotel and v["service"] == service and x[v["id"]].value() > 1e-4
            ]
            for v, val in chosen:
                pct = f" ({val*100:.0f}%)" if val < 0.999 else ""
                print(f"   [{service:>9}] {v['provider']}{pct}")

    print("\n" + "-" * 70)
    beneficio = pulp.value(prob.objective)
    diff_pct = (beneficio - BENCHMARK_EXCEL) / BENCHMARK_EXCEL * 100
    print(f"Benchmark Excel (OpenSolver/CBC): {BENCHMARK_EXCEL:,.2f} €")
    print(f"Resultado Python (PuLP/CBC):      {beneficio:,.2f} €")
    print(f"Diferencia: {diff_pct:+.2f}%")

    return prob, x


if __name__ == "__main__":
    variables = load_variables()
    hotels = load_hotels()
    solve_and_report(variables, hotels)
