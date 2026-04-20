"""Testes unitários para generation/llm.py."""

import unittest
from unittest.mock import patch, MagicMock

from core.config import settings
from core.schemas import ExpertiseLevel, UserProfile
from generation.llm import generate, build_system_prompt, SYSTEM_PROMPTS


class TestBuildSystemPrompt(unittest.TestCase):
    def test_beginner_profile_returns_beginner_prompt(self):
        profile = UserProfile(name="Test", expertise=ExpertiseLevel.beginner)
        prompt = build_system_prompt(profile)
        self.assertEqual(prompt, SYSTEM_PROMPTS[ExpertiseLevel.beginner])
        self.assertIn("linguagem simples", prompt)

    def test_intermediate_profile_returns_intermediate_prompt(self):
        profile = UserProfile(name="Test", expertise=ExpertiseLevel.intermediate)
        prompt = build_system_prompt(profile)
        self.assertEqual(prompt, SYSTEM_PROMPTS[ExpertiseLevel.intermediate])
        self.assertIn("termos técnicos com explicações breves", prompt)

    def test_expert_profile_returns_expert_prompt(self):
        profile = UserProfile(name="Test", expertise=ExpertiseLevel.expert)
        prompt = build_system_prompt(profile)
        self.assertEqual(prompt, SYSTEM_PROMPTS[ExpertiseLevel.expert])
        self.assertIn("terminologia avançada", prompt)


class TestGenerate(unittest.TestCase):
    @patch("generation.llm.ollama.chat")
    def test_messages_structure_with_history(self, mock_chat: MagicMock):
        mock_chat.return_value = {"message": {"content": "Resposta do LLM"}}

        profile = UserProfile(name="Usuario", expertise=ExpertiseLevel.beginner)
        history = [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Olá! Como posso ajudar?"},
        ]

        result = generate(
            question="Qual a melhor época para plantar soja?",
            context="A soja deve ser plantada entre outubro e dezembro.",
            history=history,
            profile=profile,
        )

        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args.kwargs
        messages = call_kwargs["messages"]

        # Verifica estrutura do messages[]
        self.assertEqual(len(messages), 4)  # system + 2 history + 1 user

        # messages[0] é sempre system prompt
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], SYSTEM_PROMPTS[ExpertiseLevel.beginner])

        # Histórico inserido corretamente
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Olá")
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[2]["content"], "Olá! Como posso ajudar?")

        # Pergunta atual com contexto RAG
        self.assertEqual(messages[3]["role"], "user")
        self.assertIn("Contexto:", messages[3]["content"])
        self.assertIn("A soja deve ser plantada", messages[3]["content"])
        self.assertIn("Pergunta: Qual a melhor época", messages[3]["content"])

        # Modelo correto
        self.assertEqual(call_kwargs["model"], settings.chat_model)

        # Retorno correto
        self.assertEqual(result, "Resposta do LLM")

    @patch("generation.llm.ollama.chat")
    def test_messages_without_history(self, mock_chat: MagicMock):
        mock_chat.return_value = {"message": {"content": "Resposta"}}

        profile = UserProfile(name="Usuario", expertise=ExpertiseLevel.expert)

        generate(
            question="Pergunta teste",
            context="Contexto teste",
            history=[],
            profile=profile,
        )

        messages = mock_chat.call_args.kwargs["messages"]

        # Apenas system + user (sem histórico)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], SYSTEM_PROMPTS[ExpertiseLevel.expert])
        self.assertEqual(messages[1]["role"], "user")

    @patch("generation.llm.ollama.chat")
    def test_messages_without_context(self, mock_chat: MagicMock):
        mock_chat.return_value = {"message": {"content": "Resposta"}}

        profile = UserProfile(name="Usuario", expertise=ExpertiseLevel.intermediate)

        generate(
            question="Pergunta sem contexto",
            context="",
            history=[],
            profile=profile,
        )

        messages = mock_chat.call_args.kwargs["messages"]
        user_message = messages[1]["content"]

        # Sem contexto, não deve ter "Contexto:"
        self.assertNotIn("Contexto:", user_message)
        self.assertIn("Pergunta: Pergunta sem contexto", user_message)

    @patch("generation.llm.ollama.chat")
    def test_each_expertise_level_uses_different_system_prompt(self, mock_chat: MagicMock):
        mock_chat.return_value = {"message": {"content": "OK"}}

        system_prompts_used = []

        for level in ExpertiseLevel:
            profile = UserProfile(name="Test", expertise=level)
            generate(question="Q", context="C", history=[], profile=profile)
            messages = mock_chat.call_args.kwargs["messages"]
            system_prompts_used.append(messages[0]["content"])

        # Todos os 3 prompts devem ser diferentes
        self.assertEqual(len(set(system_prompts_used)), 3)


class TestNoQdrantImport(unittest.TestCase):
    def test_module_does_not_import_qdrant(self):
        import generation.llm as llm_module

        # Verifica que qdrant_client não está nos imports do módulo
        module_imports = dir(llm_module)
        self.assertNotIn("QdrantClient", module_imports)
        self.assertNotIn("qdrant_client", module_imports)

        # Verifica que o módulo qdrant_client não foi importado como dependência
        with open(llm_module.__file__) as f:
            llm_source = f.read()
        self.assertNotIn("qdrant", llm_source.lower())


if __name__ == "__main__":
    unittest.main()
