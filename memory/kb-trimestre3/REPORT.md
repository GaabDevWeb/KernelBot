# KB 3º trimestre — relatório

## Contagens

| | ANTES | DEPOIS |
|--|------:|-------:|
| Rows knowledge active | 133 | 148 |
| Aulas (sem doc) | 111 | 126 |
| Disciplinas silo BM25 | 8 (+doc) | 11 (+doc) |
| Chunks BM25 | 512 | 606 |

## Adicionados
- Disciplinas: 3 (`fundamentos-csharp`, `fundamentos-java`, `projeto-bloco-backend`)
- Aulas: 15 (6+6+3)
- Professores context: Rafael Cruz, Luiz Paulo Maia, Elberth Moraes, Orlando Fonseca Guilarte
- Calendar: event-028 TP1 Java 2026-08-10; event-029 TP2 Java 2026-08-24

## Ausências (não inventadas)
- C#: datas TP/AT não calendárizadas na fonte
- Java TP3: "entorno do feriado de 7 de setembro" — sem data exacta
- Java Assessment: data não detalhada
- PB Backend: datas TP/AT específicas ausentes até aula 03

## Pipeline
- Sync ISS/jsons → KernelBot/jsons
- Whitelist `_LESSON_DISCIPLINE_DIRS`
- `./bin/ingest-jsons.sh` (UPSERT)
- Restart Kernel → rebuild BM25 (silo_count=11)
