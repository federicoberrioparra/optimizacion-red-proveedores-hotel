# De 171 variables a una decisión — Optimización de la red de proveedores de una cadena hotelera europea

Proyecto de programación lineal (Investigación Operativa) que resuelve un problema real de negocio: **cómo elegir los proveedores de servicios externos de un hotel (restauración y actividades) para maximizar el beneficio de toda una cadena**, respetando restricciones de presupuesto, calidad de marca y viabilidad por destino.

Incluye dos implementaciones del mismo modelo: la original en **Excel + OpenSolver**, y una réplica independiente en **Python + PuLP** para validar el resultado y auditar el modelo.

---

## Contexto del caso

Gran parte de la rentabilidad de un hotel no depende solo de las habitaciones, sino de los **servicios externos** que ofrece: desayuno, cena y actividades turísticas. Diseñamos el caso de una cadena hotelera europea ficticia (*Badal's Hotel*) con presencia en **19 ciudades** distribuidas en 4 zonas geográficas:

| Zona | Ciudades |
|---|---|
| Ibérica | Málaga, Madrid, Barcelona, Palma de Mallorca, Lisboa, Albufeira |
| Mediterráneo Occidental | Marsella, Lyon, París, Milán, Roma, Venecia |
| Europa Central | Berlín, Ámsterdam, Budapest |
| Mediterráneo Oriental | Atenas, Ermoupolis, Estambul, La Valeta |

**Pregunta de negocio:** ¿qué combinación de proveedores de desayuno, cena y actividades maximiza el beneficio total de la red, sin comprometer la calidad de marca ni la viabilidad económica de cada hotel?

## Objetivo

Maximizar el **beneficio anual total** de la cadena, eligiendo para cada hotel qué proveedor contratar en cada uno de los tres servicios (desayuno, cena, actividades), sujeto a:

- **Presupuesto máximo** cerrado para toda la red
- **Calidad media ponderada mínima** (posicionamiento de marca premium, no negociable)
- **Ingresos mínimos por hotel**, para garantizar la viabilidad de cada destino como unidad de negocio
- **Selección única de proveedor** en desayuno y actividades; la cena sí permite repartir el volumen entre varios proveedores

## Modelo

Programa lineal con **variables continuas 0–1**, donde cada variable representa la fracción de la demanda anual de un hotel cubierta por un proveedor concreto en un servicio concreto.

```
MAX  Z = Σ beneficio_unitario · x

s.a.
  Σ (coste_variable + coste_fijo) · x        ≤ Presupuesto
  Σ calidad · x / n_servicios                ≥ Calidad_mínima
  Σ ingreso_bruto · x  (por hotel)           ≥ Ingreso_mínimo_hotel
  Σ x  (por servicio y hotel)                ≤ 1
  0 ≤ x ≤ 1
```

Resuelto originalmente con **OpenSolver (CBC — Coin-or Branch and Cut)** en Excel, ya que el Solver estándar no soporta el volumen de variables de decisión del modelo (170 variables, más de 50 restricciones).

## Resultado

| Indicador | Valor |
|---|---|
| **Beneficio óptimo** | **120.163,25 €** |
| Presupuesto utilizado | 220.000 € (100% del disponible) |
| Calidad media de la solución | 2,96 / 5 (mínimo exigido: 2,70) |

**Hallazgos clave:**
- El **presupuesto es la única restricción estructural activa** — el freno real del modelo.
- La restricción de calidad actúa como un **"suelo de marca"**: se cumple de forma natural sin forzar la solución.
- Se identifican **soluciones degeneradas** (varias combinaciones de desayuno igualmente óptimas) en algunos destinos, lo que da margen operativo sin perder rentabilidad.

## Beneficio e ingresos por zona

![Beneficio por zona](./img/Grafico_Beneficios.png)

![Coste por zona](./img/Grafico_Costes.png)

La zona Mediterránea Occidental concentra el mayor volumen de negocio (más hoteles, mayor beneficio y mayor coste), seguida de la zona Ibérica. La zona Mediterránea Oriental, con solo 4 hoteles, genera un beneficio proporcionalmente muy competitivo respecto a su coste.

## Análisis de sensibilidad

El verdadero valor del modelo está en traducir el análisis de sensibilidad en decisiones de negocio:

| Palanca | Lectura económica |
|---|---|
| **Ampliar presupuesto** | Cada € adicional genera ~0,49 € de beneficio extra (retorno marginal ~49%) |
| **Revisar mínimos de ingresos exigidos** | Ámsterdam y Budapest penalizan el beneficio al forzar un mix subóptimo |
| **Explotar soluciones alternativas** | Varios destinos tienen múltiples combinaciones de desayuno igualmente óptimas |
| **Ampliar capacidad de actividades** | Milán, Mallorca y Budapest muestran precio sombra positivo: más capacidad = más beneficio directo |

Cabe destacar que, de las 19 ciudades del modelo, solo **estas tres** presentan una restricción de actividades realmente rentable de ampliar. En el resto, el precio sombra es nulo: la oferta actual de actividades ya cubre la demanda de forma óptima y contratar más capacidad no generaría beneficio adicional. Esto sugiere que la palanca de actividades tiene un **impacto muy localizado**, frente al presupuesto, cuyo efecto es transversal a toda la red.

## Validación cruzada: Excel vs Python

Para auditar el modelo y no depender de una única herramienta, se construyó una réplica independiente en **Python (PuLP)**, disponible en [`hoteles_lp/`](./hoteles_lp).

| | Excel (OpenSolver/CBC) | Python (PuLP/CBC) |
|---|---|---|
| Beneficio óptimo | 120.163,25 € | 120.449,41 € |
| Diferencia | — | +0,24 % |

Esta validación permitió detectar dos inconsistencias reales en las fórmulas del Excel original, documentadas y corregidas en la réplica:

1. **Restricción de coherencia desayuno-cena mal referenciada.** La fórmula original apunta a celdas que solo pueden valer entre 0 y 1, haciendo que la condición exigida (`≤ -2`) sea matemáticamente imposible de cumplir. Si se hubiera aplicado tal cual, el modelo habría sido infactible — como sí se obtuvo una solución óptima, se confirma que esta restricción nunca llegó a aplicarse realmente en la resolución.
2. **Desplazamiento de rango** en las restricciones de ingresos mínimos de los tres últimos destinos (Ermoupolis, Estambul, La Valeta), causado por un arrastre de fórmulas.

Ambos hallazgos están documentados como comentarios directamente en el código (`hoteles_lp/model.py`).

## Informe completo

El análisis detallado — planteamiento del caso, recomendación al cliente, las tres propuestas de mejora, validación cruzada y anexos con el modelo formal — está desarrollado en [`Badals_Hotel_Informe.docx`](./Badals_Hotel_Informe.docx).

## Herramientas

- Excel + **OpenSolver** (CBC solver)
- **Python + PuLP** (CBC solver) para validación cruzada del modelo
- Análisis de costes reducidos y precios sombra (informe de sensibilidad)
- Modelización por bloques (por zona geográfica) para minimizar errores de referencia

## Estructura del repositorio

```
├── Hoteles_Portfolio.xlsm       # Modelo original (variables, restricciones, sensibilidad)
├── Cas_Badals_Hotel.pdf         # Enunciado y memoria del caso
├── Badals_Hotel_Informe.docx    # Informe completo (planteamiento, recomendación, mejoras, anexos)
├── img/                          # Gráficos exportados del Excel
│   ├── Grafico_Beneficios.png
│   └── Grafico_Costes.png
├── hoteles_lp/                  # Réplica en Python (PuLP) + validación cruzada
│   ├── model.py
│   ├── requirements.txt
│   ├── data/
│   │   ├── variables.csv
│   │   └── hotels.csv
│   └── README.md
└── README.md
```

## Autor

Fede — Grau en Empresa i Tecnologia, UAB
Proyecto académico — Investigación Operativa, Curso 2025–2026

---

*Este proyecto forma parte de mi portafolio de análisis de datos y optimización aplicada a negocio.*
