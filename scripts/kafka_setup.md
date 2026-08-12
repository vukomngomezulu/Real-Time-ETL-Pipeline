# Kafka in Docker

Kafka now runs through Docker Compose. You do not need to download Kafka or run
the broker manually on Windows or Ubuntu/WSL.

## Start Kafka With the Full Project

```bash
docker compose up --build
```

The Compose stack starts a single-node Kafka broker in KRaft mode and creates
the configured topic with the `kafka-init` service.

Default topic:

```text
transactions
```

## List Topics

```bash
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:9092 --list
```

## Describe the Transactions Topic

```bash
docker compose exec kafka kafka-topics.sh \
  --bootstrap-server kafka:9092 \
  --describe \
  --topic transactions
```

## Host Access

Containers use:

```text
kafka:9092
```

Tools running directly from Ubuntu/WSL use:

```text
localhost:29092
```

That host port is controlled by `KAFKA_HOST_PORT` in `.env`.

## Reset Kafka Data

```bash
docker compose down -v
docker compose up --build
```

This removes both Kafka and Postgres volumes, so it resets all project data.
