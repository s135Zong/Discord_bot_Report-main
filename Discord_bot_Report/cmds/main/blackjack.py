# ** author: S1354008 **
#v--------------Discord_import--------------v#
import discord
from discord import app_commands
from discord.ui import View, Button
#v---------------Other_import---------------v#
from core.classes import Cog_Extension
import random
#-------------------------------------------------------------------------
CARD_EMOJIS = [
    ":regional_indicator_a:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:", ":keycap_ten:", ":regional_indicator_j:", ":regional_indicator_q:", ":regional_indicator_k:"
]
CARD_VALUES = {
    ":regional_indicator_a:": 11,
    ":two:": 2,
    ":three:": 3,
    ":four:": 4,
    ":five:": 5,
    ":six:": 6,
    ":seven:": 7,
    ":eight:": 8,
    ":nine:": 9,
    ":keycap_ten:": 10,
    ":regional_indicator_j:": 10,
    ":regional_indicator_q:": 10,
    ":regional_indicator_k:": 10
}



class BlackjackView(View):
    def __init__(self, player_hand, dealer_hand, dealer_hidden_card):
        super().__init__(timeout=None)
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.dealer_hidden_card = dealer_hidden_card
        self.message = None

    def calculate_score(self, hand):
        score = sum(CARD_VALUES[card] for card in hand)
        aces = hand.count(":regional_indicator_a:")
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score



    async def update_message(self, interaction=None):
        player_score = self.calculate_score(self.player_hand)
        dealer_score = self.calculate_score(self.dealer_hand)

        embed = discord.Embed(title="🃏 Blackjack│21點遊戲")
        embed.add_field(name="玩家的手牌", value=f"{' '.join(self.player_hand)} `總點數: {player_score}`", inline=False)
        embed.add_field(name="莊家的手牌", value=f"{self.dealer_hand[0]} :stop_button:", inline=False)

        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="加牌", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: Button):
        self.player_hand.append(random.choice(CARD_EMOJIS))
        score = self.calculate_score(self.player_hand)
        if score > 21:
            await self.end_game(interaction, busted=True)
        else:
            await self.update_message(interaction)



    @discord.ui.button(label="停止", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):
        while self.calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(random.choice(CARD_EMOJIS))

        player_score = self.calculate_score(self.player_hand)
        dealer_score = self.calculate_score(self.dealer_hand)

        result = ""
        if dealer_score > 21 or player_score > dealer_score:
            result = "你贏了！"
        elif player_score < dealer_score:
            result = "你輸了！"
        else:
            result = "平手！"

        embed = discord.Embed(title="🃏 Blackjack│21點遊戲")
        embed.add_field(name="玩家的手牌", value=f"{' '.join(self.player_hand)} `總點數: {player_score}`", inline=False)
        embed.add_field(name="莊家的手牌", value=f"{' '.join(self.dealer_hand)} `總點數: {dealer_score}`", inline=False)
        embed.add_field(name="牌局結果", value=result, inline=False)

        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

    async def end_game(self, interaction, busted):
        dealer_score = self.calculate_score(self.dealer_hand)
        embed = discord.Embed(title="🃏 Blackjack│21點遊戲")
        embed.add_field(name="玩家的手牌", value=f"{' '.join(self.player_hand)} `總點數: {self.calculate_score(self.player_hand)}`", inline=False)
        embed.add_field(name="莊家的手牌", value=f"{' '.join(self.dealer_hand)} `總點數: {dealer_score}`", inline=False)
        embed.add_field(name="牌局結果", value="你爆點了！輸了遊戲。" if busted else "遊戲結束。", inline=False)
        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)



class BlackjackCog(Cog_Extension):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackjack", description="開始一場 Blackjack│21點 遊戲")
    async def blackjack(self, interaction: discord.Interaction):
        player_hand = [random.choice(CARD_EMOJIS) for _ in range(2)]
        dealer_hand = [random.choice(CARD_EMOJIS), random.choice(CARD_EMOJIS)]

        view = BlackjackView(player_hand, dealer_hand, dealer_hidden_card=":stop_button:")

        # 建立初始 embed（莊家一張明牌、一張暗牌）
        player_score = view.calculate_score(player_hand)
        embed = discord.Embed(title="🃏 Blackjack│21點遊戲", color=discord.Color.blue())
        embed.add_field(name="玩家的手牌", value=f"{' '.join(player_hand)} `總點數: {player_score}`", inline=False)
        embed.add_field(name="莊家的手牌", value=f"{dealer_hand[0]} :stop_button:", inline=False)
        embed.set_footer(text="請選擇你的動作")

        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
#-------------------------------------------------------------------------
async def setup(bot):
    await bot.add_cog(BlackjackCog(bot))