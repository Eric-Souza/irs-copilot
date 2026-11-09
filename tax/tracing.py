# Sends spans to Phoenix when PHOENIX_COLLECTOR_ENDPOINT is set (http://localhost:6006 for a local
# `phoenix serve`). OpenInference's LlamaIndex instrumentation traces the Workflow's steps, the
# retrievals, the embedding and the model calls with their prompts, tool calls and tokens, so one
# question is one trace, with a span per tool call (Agent.tool). Without the variable nothing is
# imported and nothing is sent.

import os

PROJECT = "irs-copilot"


def trace_to_phoenix(project: str = PROJECT) -> bool:
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        return False
    from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": PROJECT, "openinference.project.name": project}))
    batch = BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))

    class Answering(SpanProcessor):
        # Splitting the publication into nodes at startup is a trace per section, hundreds of them, all noise
        def on_start(self, span, parent_context=None):
            batch.on_start(span, parent_context)

        def on_end(self, span):
            if not span.name.startswith("SentenceSplitter."):
                batch.on_end(span)

        def shutdown(self):
            batch.shutdown()

        def force_flush(self, timeout_millis=30000):
            return batch.force_flush(timeout_millis)

    provider.add_span_processor(Answering())
    trace.set_tracer_provider(provider)
    LlamaIndexInstrumentor().instrument(tracer_provider=provider)
    return True
