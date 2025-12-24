# dennett/runners/agent_runner.py
"""
AgentRunner: Adapter for running AgentExecutor.
"""

class AgentRunner:
    """Adapter for integrating AgentExecutor with AgentWorker."""
    
    def __init__(self, registry, artifact_manager=None):
        """
        Initialize agent runner.
        
        Args:
            registry: NodeRegistry for node implementations.
            artifact_manager: Optional artifact manager.
        """
        self.registry = registry
        self.artifact_manager = artifact_manager

    async def run(
        self,
        agent_executor_class,
        agent_config: dict,
        execution_id: str,
        db_session,
        cancellation_token=None,
        event_emitter=None,
    ) -> dict:
        """
        Run agent through AgentExecutor.
        
        Args:
            agent_executor_class: AgentExecutor class.
            agent_config: Agent configuration.
            execution_id: Execution ID.
            db_session: Database session.
            cancellation_token: Cancel event.
            event_emitter: Event emitter callback.
        
        Returns:
            Result from agent execution.
        """
        executor = agent_executor_class(
            agent_config=agent_config,
            execution_id=execution_id,
            db_session=db_session,
            registry=self.registry,
            event_emitter=event_emitter,
            cancellation_token=cancellation_token,
            artifact_manager=self.artifact_manager,
        )
        return await executor.run_graph()
