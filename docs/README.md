# Documentación del Proyecto

## Estructura

```
docs/
├── especificacion_mcp.md    # Especificación principal del sistema BT + MCP
├── MANUAL_MCP.md            # Manual de uso de la API MCP
├── adr/                     # Architecture Decision Records
│   └── 001-combat-detection.md
└── phase-status/            # Estado de implementación por fases
    └── phase-0-initial.md
```

## Convenciones

### ADRs (Architecture Decision Records)
Documentan decisiones arquitectónicas importantes con formato:
- **Contexto**: Problema o situación
- **Decisión**: Solución elegida
- **Consecuencias**: Pros/contras de la decisión

### Phase Status
Estado de cada fase de implementación:
- Resumen de lo completado
- Archivos modificados
- Decisiones tomadas (referencias a ADRs)
- Lecciones aprendidas
- Pendiente para siguiente fase

## Referencias

- [Especificación Principal](especificacion_mcp.md)
- [Manual MCP](MANUAL_MCP.md)
- [Estado Actual](phase-status/phase-0-initial.md)
