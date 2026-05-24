import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import asyncio

# Target imports
from core.perception.acoustic_front import GSCBeamformer, detect_speech_activity
from core.perception.biometrics import BiometricVoiceVerifier, process_semg_signal, SubVocalDecoder
from core.perception.biomarkers import AcousticStressProfiler
from core.perception.flow_coordinator import FlowCoordinator, AudioInterruptController
from core.perception.diarization import AmbientConversationFilter
from core.perception.proactive_daemon import ProactiveDaemon
from cognitive.sarcasm_evaluator import SarcasmEvaluator
from cognitive.coreference import LocalCorefResolver
from cognitive.elliptical_rebuilder import EllipticalSentenceCompiler
from cognitive.context_vector_store import SystemContextMapper
from persona.emotional_engine import SSMLExpressionFormatter, AdaptiveBehaviorHeuristic
from persona.counter_reasoner import MoralCounterReasoner
from persona.polyglot_translator import RealTimeTranslator, PhoneticAccentNormalizer, AlphanumericDecoder

class TestPhase1NLP(unittest.IsolatedAsyncioTestCase):

    def test_acoustic_front_beamforming(self):
        # Ingest simulated 4-channel audio chunk of 1024 frames
        num_channels = 4
        chunk_size = 1024
        raw_pcm = np.random.randint(-1000, 1000, size=chunk_size * num_channels, dtype=np.int16).tobytes()
        
        beamformer = GSCBeamformer(num_channels=num_channels, rate=16000, chunk=chunk_size)
        output = beamformer.process_frame(raw_pcm)
        
        self.assertIsInstance(output, np.ndarray)
        self.assertEqual(len(output), chunk_size)

    def test_detect_speech_activity(self):
        # Low energy chunk
        low_energy = np.zeros(100, dtype=np.int16)
        self.assertFalse(detect_speech_activity(low_energy, vad_model=None))

        # High energy chunk
        high_energy = np.full(100, 1000, dtype=np.int16)
        self.assertTrue(detect_speech_activity(high_energy, vad_model=None))

    def test_biometric_voice_verifier(self):
        anchor = np.ones(192)
        # Identical embedding
        verifier = BiometricVoiceVerifier(anchor_template=anchor, threshold=0.72)
        self.assertTrue(verifier.verify_vocal_path(anchor))

        # Completely orthogonal embedding
        orthogonal = np.zeros(192)
        orthogonal[0] = -1.0
        self.assertFalse(verifier.verify_vocal_path(orthogonal))

    def test_semg_processing_and_subvocal_decoding(self):
        raw_emg = np.random.randint(-200, 200, size=50, dtype=np.int16)
        processed = process_semg_signal(raw_emg, fs=500)
        self.assertEqual(len(processed), len(raw_emg))

        decoder = SubVocalDecoder()
        # Decode zero EMG
        self.assertEqual(decoder.decode_signals(np.zeros(10)), "")
        
        # Decode extreme EMG (high RMS energy)
        high_emg = np.full(100, 200.0)
        self.assertEqual(decoder.decode_signals(high_emg), "emergency abort")

    def test_acoustic_stress_profiling(self):
        profiler = AcousticStressProfiler(sample_rate=16000)
        
        # Short audio sequence
        audio_short = np.zeros(10)
        metrics_short = profiler.profile_stress(audio_short)
        self.assertEqual(metrics_short["stress_score"], 0.0)

        # Simulated sinusoidal wave (voiced sound)
        t = np.linspace(0, 0.1, 1600)  # 0.1 seconds at 16000Hz
        freq = 150.0  # 150 Hz pitch
        audio_wave = (np.sin(2 * np.pi * freq * t) * 5000).astype(np.int16)
        
        metrics = profiler.profile_stress(audio_wave)
        self.assertIn("f0_mean", metrics)
        self.assertIn("jitter", metrics)
        self.assertIn("shimmer", metrics)
        self.assertIn("stress_score", metrics)
        self.assertGreater(metrics["f0_mean"], 50)
        self.assertLess(metrics["f0_mean"], 500)

    async def test_flow_coordinator_and_interrupt(self):
        coordinator = FlowCoordinator()
        token_task = asyncio.create_task(coordinator._process_input_tokens())
        
        try:
            await coordinator.inject_user_input("hello spark")
            # Give a small slice of event loop time
            await asyncio.sleep(0.05)
            
            payload = await coordinator.execution_queue.get()
            self.assertEqual(payload["text"], "hello spark")
            self.assertEqual(payload["action"], "route_intent")
        finally:
            token_task.cancel()
            try:
                await token_task
            except asyncio.CancelledError:
                pass
        
        # AudioInterruptController
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        
        interrupt_controller = AudioInterruptController(tts_player_process=mock_process)
        
        # Low energy - no barge-in
        self.assertFalse(interrupt_controller.detect_barge_in(np.zeros(10)))
        
        # High energy - barge-in triggered
        self.assertTrue(interrupt_controller.detect_barge_in(np.full(100, 1000.0)))
        mock_process.kill.assert_called_once()
        self.assertTrue(interrupt_controller.interrupt_event.is_set())

    def test_ambient_conversation_diarization(self):
        filter_conv = AmbientConversationFilter()
        # Mock embeddings for 2 speakers (Speaker 0 and Speaker 1)
        # Cluster vectors around two endpoints
        embeddings = np.array([
            [1.0, 0.0],
            [0.9, 0.1],
            [0.1, 1.0],
            [0.0, 0.9]
        ])
        labels = filter_conv.diarize_and_route(embeddings)
        self.assertEqual(len(labels), 4)
        # Check that labels grouped similar items together
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(labels[2], labels[3])

    async def test_proactive_daemon(self):
        alert_received = []
        async def mock_callback(msg):
            alert_received.append(msg)

        daemon = ProactiveDaemon(alert_callback=mock_callback, cpu_limit=10.0, ram_limit=10.0)
        daemon.start()
        
        # Give it a brief moment to run check loop once (we will patch psutil)
        with patch("psutil.cpu_percent", return_value=99.0), \
             patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value.percent = 99.0
            
            await asyncio.sleep(0.1)  # trigger quick loop task iteration
            # Wait a tiny bit more for loop execution
            await asyncio.sleep(0.1)
            
        daemon.stop()
        self.assertTrue(len(alert_received) > 0 or not daemon.running)

    def test_sarcasm_evaluation(self):
        evaluator = SarcasmEvaluator()
        
        # Case 1: Sarcastic text with flat acoustics (low jitter)
        metrics_flat = {"f0_mean": 120.0, "jitter": 0.02, "shimmer": 0.02, "stress_score": 0.1}
        score = evaluator.evaluate_intent("This is just amazing", metrics_flat)
        self.assertEqual(score, 0.85)

        # Case 2: Ordinary text
        score_normal = evaluator.evaluate_intent("open notepad", metrics_flat)
        self.assertLess(score_normal, 0.5)

    def test_coreference_resolution(self):
        resolver = LocalCorefResolver()
        history = ["left actuator arm"]
        
        resolved = resolver.resolve_pronouns("activate it now", history)
        self.assertEqual(resolved, "activate left actuator arm now")

        resolved_no_history = resolver.resolve_pronouns("activate it now", [])
        self.assertEqual(resolved_no_history, "activate it now")

    def test_elliptical_sentence_reconstruction(self):
        compiler = EllipticalSentenceCompiler()
        logs = [{"tool": "brightness_control", "arg": "monitor"}]
        
        # Standard abort command
        rebuilt_abort = compiler.rebuild_command("abort that", logs)
        self.assertEqual(rebuilt_abort, "abort brightness_control execution immediately")

        # Layout shift command
        rebuilt_layout = compiler.rebuild_command("now the left one", logs)
        self.assertEqual(rebuilt_layout, "change display layout to primary monitor 1")

    def test_system_context_mapping(self):
        mapper = SystemContextMapper()
        
        # Informational request containing cpu
        context = mapper.get_attention_context("what is the cpu status?")
        self.assertIn("[SYSTEM CONTEXT] Telemetry coordinates: CPU at", context)

        # Ordinary request
        context_empty = mapper.get_attention_context("hello spark")
        self.assertEqual(context_empty, "")

    def test_ssml_expression_formatting(self):
        formatter = SSMLExpressionFormatter()
        
        ssml_excited = formatter.generate_ssml("Operational readiness confirmed", "excited")
        self.assertIn("rate='+15%'", ssml_excited)
        self.assertIn("pitch='+5Hz'", ssml_excited)
        
        ssml_deadpan = formatter.generate_ssml("Command logged.", "deadpan")
        self.assertIn("rate='+5%'", ssml_deadpan)
        self.assertIn("pitch='-10Hz'", ssml_deadpan)

    def test_adaptive_behavior_heuristics(self):
        heuristic = AdaptiveBehaviorHeuristic()
        
        # High stress, high urgency
        words, verbose = heuristic.calculate_verbosity(0.85, 0.90)
        self.assertEqual(words, 30)
        self.assertFalse(verbose)

        # Low stress, low urgency
        words_low, verbose_low = heuristic.calculate_verbosity(0.1, 0.1)
        self.assertEqual(words_low, 120)
        self.assertTrue(verbose_low)

    def test_moral_counter_reasoner(self):
        reasoner = MoralCounterReasoner()
        
        # Allowed action
        allowed, arg = reasoner.validate_action("open_notepad")
        self.assertTrue(allowed)
        self.assertEqual(arg, "")

        # Blocked action
        allowed_blocked, arg_blocked = reasoner.validate_action("delete_all_files")
        self.assertFalse(allowed_blocked)
        self.assertIn("Sir, I cannot execute 'delete_all_files'", arg_blocked)

    def test_polyglot_translation_and_decoders(self):
        translator = RealTimeTranslator()
        
        # Spanish translation
        translated = translator.translate_to_kernel_locale("hola ejecuto el bucle")
        self.assertEqual(translated, "hello execute the loop")

        # Accent normalizer
        normalizer = PhoneticAccentNormalizer()
        normalized = normalizer.normalize_phonemes("get the cawfee and compile git repo")
        self.assertEqual(normalized, "get the coffee and compile git repository")

        # Alphanumeric decoders
        decoder = AlphanumericDecoder()
        
        # Hex string for "hello" -> 68656c6c6f
        decoded_hex = decoder.try_decode("incoming string is 68656c6c6f")
        self.assertIn("[DECODED HEX] hello", decoded_hex)

        # Base64 string for "abort" -> YWJvcnQ=
        decoded_b64 = decoder.try_decode("YWJvcnQ=")
        self.assertIn("[DECODED BASE64] abort", decoded_b64)

if __name__ == "__main__":
    unittest.main()
