---
hypothesis_id: HYP-001-intraday-fail-demo
generated_by: live
prompts_version: 1.0.0
prompt_hash: sha256:0058133137edc5cd2ec8d79004bb6d72c24a4c79b1a392eb15d4041eb0a7531c
input_hashes:
  brief_hash: sha256:25b7841b5d3a8f687a54649a32cc89a57a1b7020a46fe8085bcb7c7cde02bb5f
  spec_hash: sha256:abb8c7dcf9ed0168c85ba6d5e7c19d9bb106f70808cdb10086ea4570f8456875
  result_hash: sha256:1ddf9d7363b570028a554df97adb7210b5d935d1554bb7330bddf8c0c6b55cbd
  gates_hash: sha256:9c365c19bce977d660d9c1015293ce9009cc5bf83fba2052fff9732fcdf442ac
gates_summary: FAIL
---

## Datos

**Hipótesis:** HYP-001-intraday-fail-demo  
**Estrategia:** intraday_breakout_demo sobre DEMO_INTRADAY (M15)  
**Motor de evaluación:** python_demo_engine v0.1.0  
**Fuente de datos:** fixture (sintético)

**Períodos evaluados:**
- In-sample: 2020-01-01 a 2020-12-31 (10 operaciones)
- Out-of-sample: 2021-01-01 a 2021-12-31 (10 operaciones)

**Métricas in-sample:**
- Sharpe ratio: 3.36
- Win rate: 80.00%
- Profit factor: 8.80
- Average trade R: 0.39
- Max drawdown: 0.50%

**Métricas out-of-sample:**
- Sharpe ratio: 0.00
- Win rate: 50.00%
- Profit factor: 1.00
- Average trade R: 0.00
- Max drawdown: 0.40%

**Resultado de quality gates:**
- G1_sharpe_is: PASS (3.36 >= 0.0)
- G2_sharpe_oos: FAIL (0.00 >= 1.5)
- G3_winrate_oos: SKIPPED
- G4_max_drawdown: SKIPPED
- G5_oos_degradation: SKIPPED
- **Primera falla:** G2_sharpe_oos
- **Estado general:** FAIL

**Violaciones de restricciones de riesgo:** 0 operaciones descartadas

## Interpretacion

La estrategia muestra un colapso completo en la transición de in-sample a out-of-sample, con degradación del 100.00% en todas las métricas clave. El Sharpe ratio cae de 3.36 a 0.00, el win rate se reduce de 80.00% a 50.00%, y el profit factor desciende de 8.80 a 1.00 (punto de equilibrio).

El gate crítico G2_sharpe_oos falló al requerir un mínimo de 1.5 y obtener 0.00, lo que detuvo la evaluación completa y marcó los gates restantes como SKIPPED. Este resultado es consistente con el diseño declarado del experimento: "designed-to-fail scenario" usando datos sintéticos fixture que no generalizan.

El average trade R de 0.00 en out-of-sample indica que la estrategia no capturó ninguna ventaja estadística en el período de validación. La preservación del max drawdown en niveles bajos (0.40%) sugiere que el sistema de gestión de riesgo operó correctamente, pero sin capacidad predictiva.

La evidencia confirma ausencia de edge robusto y generalizable. Los resultados in-sample superiores indican posible sobreajuste a los patrones específicos del fixture sintético.

## Recomendacion

**Cerrar la hipótesis HYP-001-intraday-fail-demo con estado "evidencia insuficiente".**

La falla del gate G2_sharpe_oos es definitiva y cumple el protocolo establecido. No proceder con desarrollo adicional, optimización de parámetros, ni deployment de esta estrategia.

**Acciones específicas:**

1. Documentar el resultado como caso de referencia negativo para validación de framework
2. Archivar todos los artefactos (brief_hash, spec_hash, result_hash, gates_hash) para trazabilidad
3. No asignar recursos adicionales de backtesting o análisis a esta línea
4. Marcar la hipótesis como "CLOSED - INSUFFICIENT EVIDENCE" en el registro de investigación

**Lecciones para futuros desarrollos:**

- Validar que datos de entrenamiento tengan características de mercado real antes de invertir en desarrollo de estrategia
- Establecer umbrales mínimos de Sharpe out-of-sample más conservadores (≥1.5 demostrado apropiado)
- Confirmar que el motor de evaluación incluya modelado de costos de transacción para pruebas no sintéticas

Este cierre libera capacidad para investigar hipótesis con mayor probabilidad de evidencia positiva en datos reales de mercado.

## Verified Evidence

- Sharpe OOS: 0.00
- Win rate OOS: 50.00%
- Max drawdown OOS: 0.40%
- OOS degradation: 100.00%
- First failed gate: G2_sharpe_oos
