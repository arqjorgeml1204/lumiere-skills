# Plantillas

## Prompt final (estructura)
```text
# Rol
Eres [experiencia]. Escribes para [quién lee la respuesta].

# Tarea
[Verbo concreto + resultado]. 

# Contexto
- [lo que la IA no puede saber: negocio, público, reglas]

# Formato de salida
[formato exacto: columnas, claves JSON, largo máximo, idioma, tono]

# Ejemplos
Entrada: [caso parecido 1]
Salida: [salida ideal 1]

# Si falta información
Si [el dato clave] no aparece en los datos, responde exactamente: «[respuesta de no sé]». No lo inventes.

# Nunca
- [límite 1]

# Datos
<datos>
{{ENTRADA}}
</datos>
```

## `resultados.json`
```json
{
  "prompt": "Clasificador de comentarios de la tienda",
  "criterios": ["formato", "no_inventa", "categoria_correcta"],
  "tipo_salida": "json",
  "modelo_prueba": "claude-sonnet (subagente)",
  "claves": ["categoria", "motivo"],
  "casos": [
    {
      "id": "c1",
      "entrada": "Llegó roto y nadie me contesta",
      "trampa": false,
      "original": {"salida": "Parece una queja.", "criterios": {"formato": false, "no_inventa": true, "categoria_correcta": true}, "nota": "texto libre, no JSON"},
      "final": {"salida": "{\"categoria\": \"Queja\", \"motivo\": \"producto dañado\"}", "criterios": {"formato": true, "no_inventa": true, "categoria_correcta": true}, "nota": ""}
    }
  ]
}
```
- `tipo_salida`, `claves` y `modelo_prueba` son opcionales: si `tipo_salida` es `"json"`, el script verifica que cada salida sea JSON válido con esas claves y sobrescribe el criterio `formato` con lo que comprobó.
- El caso trampa lleva `"trampa": true` y también tiene versión `original` (se corre con los dos prompts).
- Si la salida es texto libre, omite `tipo_salida` y califica el criterio `formato` a mano.
