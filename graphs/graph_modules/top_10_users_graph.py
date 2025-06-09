"""
Top 10 users graph for TGraph Bot.

This module inherits from BaseGraph and uses Seaborn to plot the top 10 users.
"""

import logging
from typing import Any

import seaborn as sns

from .base_graph import BaseGraph

logger = logging.getLogger(__name__)


class Top10UsersGraph(BaseGraph):
    """Graph showing the top 10 users by play count."""
    
    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize the top 10 users graph.
        
        Args:
            **kwargs: Additional arguments passed to BaseGraph
        """
        super().__init__(**kwargs)
        
    def get_title(self) -> str:
        """
        Get the title for this graph type.
        
        Returns:
            The graph title
        """
        return "Top 10 Users"
        
    def generate(self, data: dict[str, Any]) -> str:
        """
        Generate the top 10 users graph using the provided data.
        
        Args:
            data: Dictionary containing user activity data
            
        Returns:
            Path to the generated graph image file
        """
        logger.info("Generating top 10 users graph")
        
        try:
            # Setup figure and axes
            fig, ax = self.setup_figure()
            
            # TODO: Implement actual graph generation using Seaborn
            # This will process the data and create a horizontal bar plot
            # showing the top 10 users by play count
            # Should respect CENSOR_USERNAMES configuration option
            
            # Placeholder implementation
            ax.text(0.5, 0.5, "Top 10 Users Graph\n(Not yet implemented)", 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title(self.get_title(), fontsize=18, fontweight='bold')
            
            # TODO: Apply Seaborn styling
            # sns.set_style("whitegrid")
            # sns.barplot(data=processed_data, x="play_count", y="username", ax=ax, orient="h")
            
            # Save the figure
            output_path = "graphs/top_10_users.png"
            return self.save_figure(output_path)
            
        except Exception as e:
            logger.exception(f"Error generating top 10 users graph: {e}")
            raise
        finally:
            self.cleanup()
