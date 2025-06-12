# cmds/games/gomoku.py

# ** author: S1354001劉羿宗 **

#v--------------Discord_import--------------v#
import discord
from discord import app_commands
from discord.ext import commands
#v---------------Other_import---------------v#
import random
import asyncio
from typing import Optional, Dict, Tuple, Union, List 
import os 
import json 

#v------------LLM_API_Import---------------v#
import google.generativeai as genai

#v------------Data_preprocessing------------v#
try:
    from core.classes import Cog_Extension
except ImportError:
    class Cog_Extension(commands.Cog):
        def __init__(self, bot): self.bot = bot

# --- LLM API Configuration ---
gemini_model = None 
MAX_HISTORY_MESSAGES = 10 

try:
    setting_json_path = os.path.join("Discord_bot_Report", "json", "setting.json") 
    print(f"[API_CONFIG_DEBUG] Attempting to load setting.json from CWD-relative: '{setting_json_path}' (Absolute: '{os.path.abspath(setting_json_path)}')")
    with open(setting_json_path, "r", encoding="utf-8") as f: jfile = json.load(f)
    GOOGLE_API_KEY = jfile.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY: 
        print("警告：未能從 setting.json 獲取 GOOGLE_API_KEY 或其值為空。Gemini AI 功能將受限。")
        gemini_model = None
    else:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20') 
        print(f"Gemini API 已成功配置，使用模型: {gemini_model.model_name}")
except FileNotFoundError: 
    print(f"錯誤：setting.json 未在預期路徑 '{os.path.abspath(setting_json_path)}' 找到。Gemini AI 功能將受限。")
    gemini_model = None
except KeyError: 
    print("錯誤：setting.json 中未找到 'GOOGLE_API_KEY' 鍵。Gemini AI 功能將受限。")
    gemini_model = None
except Exception as e: 
    print(f"配置 Gemini API 時發生一般錯誤: {e}")
    gemini_model = None

# --- 五子棋遊戲常數 ---
BOARD_SIZE = 15; EMPTY_SLOT_EMOJI = "🟫"; PLAYER_1_EMOJI = "⚫"; PLAYER_2_EMOJI = "⚪" 
HUMAN_COLUMN_LABELS_FOR_DISPLAY = [chr(ord('𝓐') + i) for i in range(BOARD_SIZE)] 
HUMAN_ROW_LABELS_FOR_DISPLAY = [f"{i+1:02d}" for i in range(BOARD_SIZE)] 
TOP_LEFT_PLACEHOLDER = "　　" 
STANDARD_COLUMN_LABELS = [chr(ord('A') + i) for i in range(BOARD_SIZE)]

# --- 五子棋遊戲實例邏輯類別 ---
class GomokuGameInstance:
    def __init__(self, player1: discord.User, player2_or_ai: Union[discord.User, discord.Member, str], p1_is_black: bool): 
        self.board = [[EMPTY_SLOT_EMOJI for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.player1_user: discord.User = player1
        self.is_ai_game: bool = isinstance(player2_or_ai, str) and player2_or_ai == "AI"
        self.player2_user: Optional[Union[discord.User, discord.Member]] = None # Can be User or Member for PvP
        self.p1_plays_black: bool = p1_is_black
        if self.is_ai_game:
            self.ai_plays_black: bool = not p1_is_black
            self.current_turn_is_p1: bool = p1_is_black
        else: 
            if not isinstance(player2_or_ai, (discord.User, discord.Member)):
                raise TypeError(f"PvP game init error: player2_or_ai must be a discord.User or discord.Member, got {type(player2_or_ai)}")
            self.player2_user = player2_or_ai 
            self.ai_plays_black = False 
            self.current_turn_is_p1: bool = p1_is_black
        self.moves_made: int = 0; self.game_over: bool = False
        self.winner: Optional[Union[discord.User, discord.Member, str]] = None; self.winner_piece: Optional[str] = None
        self.is_draw: bool = False; self.last_move_coords: Optional[Tuple[int, int]] = None
        self.game_message: Optional[discord.Message] = None; self.last_ai_evaluation: Optional[str] = None
        self.gemini_conversation_history: List[Dict[str, Union[str, List[Dict[str,str]]]]] = [] 

    def get_current_player_user_object(self) -> Optional[Union[discord.User, discord.Member]]:
        if self.game_over: return None
        if self.current_turn_is_p1: return self.player1_user
        return None if self.is_ai_game else self.player2_user

    def get_current_player_piece_emoji(self) -> str: 
        if self.current_turn_is_p1: return PLAYER_1_EMOJI if self.p1_plays_black else PLAYER_2_EMOJI
        if self.is_ai_game: return PLAYER_1_EMOJI if self.ai_plays_black else PLAYER_2_EMOJI
        return PLAYER_2_EMOJI if self.p1_plays_black else PLAYER_1_EMOJI 
    
    def get_current_player_display_name(self) -> str: 
        if self.game_over: return "遊戲已結束"
        if self.current_turn_is_p1: return self.player1_user.mention
        if self.is_ai_game: return "Gemini AI"
        return self.player2_user.mention if self.player2_user else "對手"

    def switch_turn(self): 
        self.current_turn_is_p1 = not self.current_turn_is_p1
        print(f"[DEBUG switch_turn] Turn switched. Current is_P1_turn: {self.current_turn_is_p1}")
    
    def place_piece(self, r_idx:int,c_idx:int, piece_emoji: str) -> bool:
        print(f"[DEBUG place_piece] Attempt: {piece_emoji} at internal ({r_idx},{c_idx}). Current content: '{self.board[r_idx][c_idx] if 0<=r_idx<BOARD_SIZE and 0<=c_idx<BOARD_SIZE else 'OutOfB'}'")
        if not(0<=r_idx<BOARD_SIZE and 0<=c_idx<BOARD_SIZE and self.board[r_idx][c_idx]==EMPTY_SLOT_EMOJI): 
            print(f"[DEBUG place_piece] Placement FAILED for internal ({r_idx},{c_idx})."); return False
        self.board[r_idx][c_idx]=piece_emoji;self.moves_made+=1;self.last_move_coords=(r_idx,c_idx)
        print(f"[DEBUG place_piece] Placement SUCCESS for internal ({r_idx},{c_idx}). Moves: {self.moves_made}"); return True
    
    def check_for_win(self,r_idx:int,c_idx:int) -> bool: 
        pob=self.board[r_idx][c_idx]; wd=False; 
        if pob==EMPTY_SLOT_EMOJI: return False
        for dr,dc in[(0,1),(1,0),(1,1),(1,-1)]:
            ct=1;
            for i in range(1,5):nr,nc=r_idx+dr*i,c_idx+dc*i;ct+=(0<=nr<BOARD_SIZE and 0<=nc<BOARD_SIZE and self.board[nr][nc]==pob)
            for i in range(1,5):nr,nc=r_idx-dr*i,c_idx-dc*i;ct+=(0<=nr<BOARD_SIZE and 0<=nc<BOARD_SIZE and self.board[nr][nc]==pob)
            if ct>=5:wd=True;break
        if wd:
            self.game_over=True;self.winner_piece=pob;print(f"[DEBUG check_for_win] Win by {self.winner_piece} at internal ({r_idx},{c_idx})")
            if self.current_turn_is_p1: self.winner = self.player1_user
            else: self.winner = "Gemini AI" if self.is_ai_game else self.player2_user
            print(f"[DEBUG check_for_win] Winner set to: {self.winner}"); return True
        if self.moves_made>=BOARD_SIZE*BOARD_SIZE:
            self.game_over=True;self.is_draw=True;print(f"[DEBUG check_for_win] Draw. Moves made: {self.moves_made}");return False 
        return False 
    
    def format_board_for_gemini(self) -> str: 
        pp=[]; ai_color_str, human_color_str = "", ""
        if self.is_ai_game:
            ai_color_str = "黑" if self.ai_plays_black else "白"
            human_color_str = "黑" if self.p1_plays_black else "白"
        for r_idx in range(BOARD_SIZE):
            for c_idx in range(BOARD_SIZE):
                pe=self.board[r_idx][c_idx]
                if pe!=EMPTY_SLOT_EMOJI:
                    gemini_col_label = STANDARD_COLUMN_LABELS[c_idx]; gemini_row_label = str(r_idx+1)   
                    is_p1s_actual_piece = (pe == PLAYER_1_EMOJI and self.p1_plays_black) or \
                                          (pe == PLAYER_2_EMOJI and not self.p1_plays_black)
                    pchar = ""
                    if self.is_ai_game: pchar = human_color_str if is_p1s_actual_piece else ai_color_str
                    else: pchar = "黑" if is_p1s_actual_piece else "白"
                    pp.append(f"{gemini_col_label}{gemini_row_label}:{pchar}")
        if not pp:return"棋盤目前是空的。"
        your_prompt_color = ai_color_str if self.is_ai_game else ("黑" if self.p1_plays_black else "白") 
        opp_prompt_color = human_color_str if self.is_ai_game else ("白" if self.p1_plays_black else "黑")
        if self.is_ai_game:
             return f"當前棋盤狀態（你是執{ai_color_str}棋，對手執{human_color_str}棋，空位未列出）："+" ".join(pp)
        return "PvP棋盤狀態(不應由此函數生成給AI的prompt): " + " ".join(pp) 
    
    def format_board_for_discord(self) -> str: 
        h=TOP_LEFT_PLACEHOLDER+" ".join(HUMAN_COLUMN_LABELS_FOR_DISPLAY)+"\n";ls=[f"{HUMAN_ROW_LABELS_FOR_DISPLAY[i]} {''.join(self.board[i])}"for i in range(BOARD_SIZE)];b="\n".join(ls)
        return f"```\n{h}{b}\n```"
    
    def get_status_message(self) -> str: 
        if self.game_over:
            wpd=self.winner_piece or'(?)'
            wmd=(self.winner.mention if isinstance(self.winner,(discord.User, discord.Member))else str(self.winner))if self.winner else"未知"
            if self.winner:return f"🎉 **遊戲結束！ {wmd} ({wpd}) 獲勝！** 🎉"
            elif self.is_draw:return"🤝 **遊戲結束！雙方平局！** 🤝"
            return"遊戲結束。"
        cdn,cpe=self.get_current_player_display_name(),self.get_current_player_piece_emoji()
        if self.is_ai_game and not self.current_turn_is_p1: return f"🤔 {cdn} ({cpe}) 正在思考..."
        return f"➡️ **輪到：** {cdn} ({cpe})"

# --- Challenge UI ---
class ChallengeAcceptView(discord.ui.View):
    def __init__(self, challenger: discord.User, challenged: Union[discord.User, discord.Member], gomoku_cog: 'Gomoku'): 
        super().__init__(timeout=180.0)
        self.challenger = challenger 
        self.challenged = challenged 
        self.gomoku_cog = gomoku_cog
        self.accepted: Optional[bool] = None
        self.message: Optional[discord.Message] = None
        print(f"[DEBUG ChallengeAcceptView.__init__] Challenger: {challenger} (Type: {type(challenger)}), Challenged: {challenged} (Type: {type(challenged)})")

    @discord.ui.button(label="接受挑戰", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[DEBUG ChallengeAcceptView.accept] Challenged user object: {self.challenged} (Type: {type(self.challenged)})")
        if interaction.user.id != self.challenged.id: await interaction.response.send_message("這個挑戰不是給你的！", ephemeral=True); return
        self.accepted = True
        for item in self.children: item.disabled = True 
        try: await interaction.message.edit(content=f"{self.challenged.mention} 已接受來自 {self.challenger.mention} 的五子棋挑戰！", view=self)
        except discord.NotFound: pass
        await self.gomoku_cog._start_new_game(interaction, self.challenger, player2_or_ai_for_start=self.challenged, ai_game=False)
        self.stop()

    @discord.ui.button(label="拒絕挑戰", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_valid=(interaction.user.id==self.challenged.id or interaction.user.id==self.challenger.id)
        if not is_valid: await interaction.response.send_message("你無法與此挑戰互動。", ephemeral=True); return
        action = "拒絕了" if interaction.user.id == self.challenged.id else "取消了"
        self.accepted = False
        for item in self.children: item.disabled = True 
        msg_c = f"{self.challenger.mention}與{self.challenged.mention}間的五子棋挑戰已被{action}。"
        try:
            if not interaction.response.is_done(): await interaction.response.edit_message(content=msg_c, view=self)
            else: await interaction.followup.edit_message(interaction.message.id, content=msg_c, view=self) 
        except Exception: pass 
        if interaction.channel_id in self.gomoku_cog.pending_challenges: 
            pending = self.gomoku_cog.pending_challenges[interaction.channel_id] 
            if pending['challenger_id']==self.challenger.id and pending['challenged_id']==self.challenged.id:
                 del self.gomoku_cog.pending_challenges[interaction.channel_id] 
        self.stop()

    async def on_timeout(self):
        if self.accepted is None:
            for item in self.children: item.disabled = True 
            if self.message:
                try: await self.message.edit(content=f"來自{self.challenger.mention}給{self.challenged.mention}的五子棋挑戰已過期。", view=self)
                except: pass
            if self.message and self.message.channel.id in self.gomoku_cog.pending_challenges: 
                pending = self.gomoku_cog.pending_challenges[self.message.channel.id] 
                if pending['challenger_id']==self.challenger.id and pending['challenged_id']==self.challenged.id:
                    del self.gomoku_cog.pending_challenges[self.message.channel.id] 
        self.stop()

#---------------------------------------------------------------
class Gomoku(Cog_Extension):
    gomoku_cmds = app_commands.Group(name="gomoku", description="遊玩五子棋遊戲")
    
    def __init__(self, bot: commands.Bot): 
        super().__init__(bot);self.active_games:Dict[int,GomokuGameInstance]={};self.gemini_model=gemini_model
        self.pending_challenges: Dict[int, Dict] = {} 

    async def _create_game_embed(self, game: GomokuGameInstance) -> discord.Embed: 
        is_ai_winner = isinstance(game.winner,str) and game.winner=="Gemini AI";color=discord.Color.blue()
        if game.game_over:color=discord.Color.green()if isinstance(game.winner,(discord.User, discord.Member))or is_ai_winner else(discord.Color.gold()if game.is_draw else color)
        embed=discord.Embed(title="五子棋(Gomoku)",description=game.format_board_for_discord(),color=color);s_msg=game.get_status_message()
        if game.is_ai_game and game.current_turn_is_p1 and game.last_ai_evaluation: 
            s_msg += f"\n\n🤖 Gemini AI 評價：\n{game.last_ai_evaluation}" 
        embed.add_field(name="狀態",value=s_msg,inline=False)
        if game.game_over:
            wd=str(game.winner.display_name if isinstance(game.winner,(discord.User, discord.Member)) else game.winner if isinstance(game.winner, str) else "未知")
            if game.winner:embed.set_footer(text=f"遊戲結束。勝利者：{wd}")
            elif game.is_draw:embed.set_footer(text="遊戲結束，平局。")
            else:embed.set_footer(text="遊戲結束。")
        else:
            p1_actual_char = PLAYER_1_EMOJI if game.p1_plays_black else PLAYER_2_EMOJI
            p2n, p2_actual_char = "", ""
            if game.is_ai_game:
                p2_actual_char = PLAYER_1_EMOJI if game.ai_plays_black else PLAYER_2_EMOJI
                p2n = "Gemini AI"
            elif game.player2_user: 
                p2_actual_char = PLAYER_2_EMOJI if game.p1_plays_black else PLAYER_1_EMOJI 
                p2n = game.player2_user.display_name
            else: p2n = "對手"; p2_actual_char = "?" 
            embed.set_footer(text=f"對戰：{game.player1_user.display_name}({p1_actual_char}) vs {p2n}({p2_actual_char})")
        return embed

    async def _update_game_display(self, game: GomokuGameInstance, interaction: discord.Interaction, content: Optional[str]=None): 
        lp="[DEBUG]_update_game_display:";print(f"{lp}IntID:{interaction.id},PrevMsg:{game.game_message.id if game.game_message else'N'},Resp:{interaction.response.is_done()}")
        embed=await self._create_game_embed(game)
        if game.game_message:
            try: await game.game_message.delete();print(f"{lp}DelOldOK:{game.game_message.id}");game.game_message=None
            except Exception as e_del:print(f"{lp}FailDelOld(MsgID:{game.game_message.id if game.game_message else 'N/A'}):{e_del}");game.game_message=None
        
        if not interaction.response.is_done():print(f"{lp}Interaction {interaction.id} not deferred,deferring.");await interaction.response.defer()
        
        try:
            msg=await interaction.followup.send(content=content,embed=embed,wait=True);game.game_message=msg;print(f"{lp}NewMsgViaFollowup for {interaction.id}:{msg.id}")
        except Exception as e:
            print(f"{lp}Followup/Resp ERR for {interaction.id}:{e}");
            if interaction.channel and game.game_message is None:print(f"{lp}LastResort for {interaction.id}")
            try:game.game_message=await interaction.channel.send(content=content,embed=embed) # type: ignore
            except Exception as e_ch:print(f"{lp}DirectSendFAIL for {interaction.id}:{e_ch}")

    async def _start_new_game(self, interaction: discord.Interaction, p1: discord.User, 
                              player2_or_ai_for_start: Optional[Union[discord.User, discord.Member, str]] = "AI", 
                              ai_game: bool = True): 
        lp="[DEBUG]_start_new_game:"
        actual_type_p2 = type(player2_or_ai_for_start)
        is_user_instance = isinstance(player2_or_ai_for_start, discord.User)
        is_member_instance = isinstance(player2_or_ai_for_start, discord.Member)
        print(f"{lp}IntID:{interaction.id}, IsAI_flag:{ai_game}, P2Val:'{player2_or_ai_for_start}', P2Type:{actual_type_p2}, IsUser:{is_user_instance}, IsMember:{is_member_instance}")
        
        chid=interaction.channel_id
        if chid in self.active_games and not self.active_games[chid].game_over:mc="此頻道已有遊戲.";await(interaction.response.send_message(mc,ephemeral=True)if not interaction.response.is_done()else interaction.followup.send(mc,ephemeral=True));return
        
        if chid in self.pending_challenges:
            if not ai_game and isinstance(player2_or_ai_for_start, (discord.User, discord.Member)): 
                if self.pending_challenges[chid]['challenger_id']==p1.id and self.pending_challenges[chid]['challenged_id']==player2_or_ai_for_start.id: del self.pending_challenges[chid]
            elif ai_game: del self.pending_challenges[chid]

        game:GomokuGameInstance;sc:str
        p1_is_black_val = random.choice([True,False])

        if ai_game or (isinstance(player2_or_ai_for_start, str) and player2_or_ai_for_start == "AI"): # Explicitly AI game
            game=GomokuGameInstance(p1,player2_or_ai="AI",p1_is_black=p1_is_black_val)
            self.active_games[chid]=game
            p1_cs,ai_cs="黑棋(先手)"if p1_is_black_val else"白棋(後手)","黑棋(先手)"if not p1_is_black_val else"白棋(後手)"
            sc=f"{p1.mention}({p1_cs})開始與Gemini AI({ai_cs})的五子棋！"
            if not interaction.response.is_done():await interaction.response.defer()
            await self._update_game_display(game,interaction,content=sc)
            if not game.current_turn_is_p1: 
                print(f"{lp}AI starts.Trigger.");await self._handle_gemini_ai_turn(game,interaction) 
        
        elif isinstance(player2_or_ai_for_start, (discord.User, discord.Member)): # PvP game
            print(f"{lp} PvP Game Path Selected. P2 is a User or Member.")
            game=GomokuGameInstance(p1,player2_or_ai=player2_or_ai_for_start,p1_is_black=p1_is_black_val)
            self.active_games[chid]=game
            p1_color_pvp = "黑棋(先手 ⚫)" if p1_is_black_val else "白棋(後手 ⚪)"
            p2_color_pvp = "白棋(後手 ⚪)" if p1_is_black_val else "黑棋(先手 ⚫)"
            sc=f"{p1.mention}({p1_color_pvp}) 開始了與 {player2_or_ai_for_start.mention}({p2_color_pvp}) 的五子棋遊戲！" # type: ignore
            if not interaction.response.is_done(): 
                try:await interaction.response.defer(thinking=False,ephemeral=True);print(f"{lp}Deferred button interaction.")
                except discord.InteractionResponded:print(f"{lp}Button interaction already responded.")
            await self._update_game_display(game,interaction,content=sc)
            if not game.current_turn_is_p1: 
                 print(f"{lp}PvP: Player 2 ({player2_or_ai_for_start.display_name}) is Black and starts.") # type: ignore
        else:
            actual_type_p2_final = type(player2_or_ai_for_start) 
            print(f"{lp} ERROR PATH: ai_game is False, and P2 is not a discord.User or discord.Member instance. P2Type was {actual_type_p2_final}")
            err="遊戲啟動錯誤：未能正確識別 PvP 對手類型。"
            if not interaction.response.is_done():await interaction.response.send_message(err,ephemeral=True)
            else:await interaction.followup.send(err,ephemeral=True);return

    @gomoku_cmds.command(name="start", description="開始五子棋遊戲。")
    @app_commands.describe(opponent="挑戰一位玩家 (可選，留空則與 Gemini AI 對戰)。")
    async def gomoku_start(self, interaction: discord.Interaction, opponent: Optional[discord.Member] = None):
        lp="[DEBUG]/gomoku_start:";chid=interaction.channel_id;
        print(f"{lp}User:{interaction.user.id}, Opponent_val:{opponent}, Opponent_type:{type(opponent)}")
        if chid in self.active_games and not self.active_games[chid].game_over:await interaction.response.send_message("此頻道已有遊戲。",ephemeral=True);return
        if chid in self.pending_challenges and opponent:await interaction.response.send_message("此頻道已有待處理挑戰。",ephemeral=True);return
        if opponent and opponent.bot:await interaction.response.send_message("不能挑戰機器人。",ephemeral=True);return
        if opponent and opponent.id==interaction.user.id:await interaction.response.send_message("不能挑戰自己！",ephemeral=True);return
        
        if opponent: 
            if not isinstance(opponent, discord.Member): 
                await interaction.response.send_message(f"錯誤：未能正確識別對手 '{opponent}'。", ephemeral=True); return
            print(f"{lp}Challenging:{opponent.id}");self.pending_challenges[chid]={'challenger_id':interaction.user.id,'challenged_id':opponent.id}
            view=ChallengeAcceptView(interaction.user,opponent,self);await interaction.response.send_message(f"{opponent.mention}，{interaction.user.mention}向你發起了五子棋挑戰！",view=view)
            view.message=await interaction.original_response()
        else: 
            if not interaction.response.is_done(): await interaction.response.defer() 
            await self._start_new_game(interaction,interaction.user, player2_or_ai_for_start="AI", ai_game=True)

    @gomoku_cmds.command(name="place",description="放置您的棋子。")
    @app_commands.describe(coordinate="座標，例如：H8 (H列第8行)。")
    async def gomoku_place(self,interaction:discord.Interaction,coordinate:str): 
        lp="[DEBUG]/gomoku_place:";chid=interaction.channel_id;print(f"{lp}User:{interaction.user.id},Coord:{coordinate}")
        if chid not in self.active_games or self.active_games[chid].game_over:await interaction.response.send_message("此頻道無進行中遊戲。",ephemeral=True);return
        game=self.active_games[chid]
        
        current_human_player_expected_to_move = game.get_current_player_user_object()
        if not current_human_player_expected_to_move or interaction.user.id != current_human_player_expected_to_move.id:
            await interaction.response.send_message("還沒輪到你，或你不是此局的當前玩家！",ephemeral=True);return
        
        try: 
            if not(2<=len(coordinate)<=3):raise ValueError("len")
            col_in,row_in=coordinate[0].upper(),coordinate[1:]
            if not(col_in in STANDARD_COLUMN_LABELS and row_in.isdigit()and 1<=int(row_in)<=15):raise ValueError("fmt A-O Col,1-15 Row")
            c_idx,r_idx=STANDARD_COLUMN_LABELS.index(col_in),int(row_in)-1 
        except Exception as e:await interaction.response.send_message(f"無效座標:'{coordinate}'.格式:H8(H列,8行).Err:{e}",ephemeral=True);return
        
        pp=game.get_current_player_piece_emoji()
        if not game.place_piece(r_idx,c_idx,pp):await interaction.response.send_message("無效移動!該位置可能已被佔用。",ephemeral=True);return
        
        if not interaction.response.is_done():print(f"{lp}Deferring {interaction.id}");await interaction.response.defer()
        
        if game.check_for_win(r_idx,c_idx):print(f"{lp}Player wins.");await self._update_game_display(game,interaction,content="遊戲結束！");return
        if game.is_draw:print(f"{lp}Draw.");await self._update_game_display(game,interaction,content="平局！");return
        
        game.switch_turn() 
        
        if game.is_ai_game and not game.current_turn_is_p1: 
            print(f"{lp}GeminiAI's turn.");
            await self._update_game_display(game,interaction) 
            await self._handle_gemini_ai_turn(game,interaction)
        else: 
            await self._update_game_display(game,interaction)

    async def _call_gemini_api(self, messages_for_api: List[Dict[str, any]], game: GomokuGameInstance) -> str:
        lp="[DEBUG]_call_gemini_api:"
        if not self.gemini_model: return "ERROR_NO_MODEL\nGemini模型未配置"
        print(f"{lp}Sending {len(messages_for_api)} msgs. Last user prompt (start): {messages_for_api[-1]['parts'][0]['text'][:100] if messages_for_api and messages_for_api[-1]['role']=='user' else 'N/A' }...")
        try:
            response = await asyncio.to_thread(self.gemini_model.generate_content, messages_for_api, 
                                               generation_config=genai.types.GenerationConfig(temperature=0.7)) 
            if response.candidates and response.candidates[0].content.parts:
                res_text = response.candidates[0].content.parts[0].text
                print(f"{lp}Resp(start):{res_text[:100]}...")
                game.gemini_conversation_history.append({'role': 'model', 'parts': [{'text': res_text}]})
                if len(game.gemini_conversation_history) > MAX_HISTORY_MESSAGES:
                    game.gemini_conversation_history = game.gemini_conversation_history[-MAX_HISTORY_MESSAGES:]
                    print(f"{lp}History trimmed to {len(game.gemini_conversation_history)} entries.")
                return res_text
            efb_text = str(response.prompt_feedback) if response.prompt_feedback else "未知原因"
            print(f"{lp}NoValidContent in Gemini response: {efb_text}");
            return f"ERROR_EMPTY_RESPONSE\nGemini未能回應. 原因:{efb_text}"
        except Exception as e:
            print(f"{lp}GeminiAPIFail:{e}");
            return f"ERROR_API_EXCEPTION\n調用API出錯:{type(e).__name__}"

    async def _parse_gemini_response(self, response_text: str) -> Tuple[Optional[str], Optional[str]]: 
        lines=response_text.strip().split('\n');move,val=None,None
        if lines:move=lines[0].strip() 
        if len(lines)>1:val=' '.join(l.strip()for l in lines[1:]if l.strip()) 
        if not(move and 2<=len(move)<=3 and'A'<=move[0].upper()<='O'and move[1:].isdigit()and 1<=int(move[1:])<=15):print(f"[DEBUG]InvalidGeminiMoveFMT:'{move}'");move=None
        if move is None and val is None:val="Gemini回應格式錯誤或移動無效"
        return move,val

    async def _handle_gemini_ai_turn(self, game: GomokuGameInstance, interaction: discord.Interaction): 
        lp="[DEBUG]_handle_gemini_ai_turn:";print(f"{lp}IntID:{interaction.id},HistLenBeforeSend:{len(game.gemini_conversation_history)}")
        ai_color_char_prompt = "黑" if game.ai_plays_black else "白"
        human_color_char_prompt = "黑" if game.p1_plays_black else "白"
        ai_piece_emoji_prompt = PLAYER_1_EMOJI if game.ai_plays_black else PLAYER_2_EMOJI
        board_state_str = game.format_board_for_gemini() 
        current_turn_user_prompt_text = f"""我們來玩五子棋遊戲。棋盤是15×15，列標籤從A到O，行標籤從1到15。
你是執{ai_color_char_prompt}棋 ({ai_piece_emoji_prompt})。你的對手執{human_color_char_prompt}棋。
{board_state_str}
你是一位世界上最強的五子棋專家。你的目標是阻止對手獲勝，並盡可能贏得比賽。
請嚴格按照以下格式輸出你的下一步 (例如 H8 代表 H列第8行)，並以詼諧的口吻評價玩家的棋路。除此之外不要添加任何其他解釋或對話。
格式範例:
H8
你真的太囂張了！

現在輪到你 ({ai_color_char_prompt}棋) 了。你的決定是？"""
        if board_state_str=="棋盤目前是空的." and game.ai_plays_black :current_turn_user_prompt_text+="\n你執黑棋，請下第一步。"
        messages_for_api = list(game.gemini_conversation_history) 
        messages_for_api.append({'role': 'user', 'parts': [{'text': current_turn_user_prompt_text}]})
        if len(messages_for_api) > MAX_HISTORY_MESSAGES: messages_for_api = messages_for_api[-MAX_HISTORY_MESSAGES:]
        
        # Add user's prompt to history BEFORE calling API
        game.gemini_conversation_history.append({'role': 'user', 'parts': [{'text': current_turn_user_prompt_text}]})
        if len(game.gemini_conversation_history) > MAX_HISTORY_MESSAGES:
            game.gemini_conversation_history = game.gemini_conversation_history[-MAX_HISTORY_MESSAGES:]

        raw_res=await self._call_gemini_api(messages_for_api, game) # Pass the updated list
        
        gem_move_str,gem_eval=await self._parse_gemini_response(raw_res) 
        game.last_ai_evaluation=gem_eval if gem_eval else"AI評價失敗或未提供"
        
        valid_mv=False
        if gem_move_str:
            try: 
                col_c_gem,row_s_gem=gem_move_str[0].upper(),gem_move_str[1:]
                if not('A'<=col_c_gem<='O'and row_s_gem.isdigit()and 1<=int(row_s_gem)<=15):raise ValueError("coord_fmt_gemini_std_letter")
                c_idx,r_idx=STANDARD_COLUMN_LABELS.index(col_c_gem),int(row_s_gem)-1 
                ai_actual_piece_emoji=PLAYER_1_EMOJI if game.ai_plays_black else PLAYER_2_EMOJI
                if game.place_piece(r_idx,c_idx,ai_actual_piece_emoji):
                    print(f"{lp}GeminiPlaced {col_c_gem}{row_s_gem} (internal {r_idx},{c_idx})");valid_mv=True
                    if game.check_for_win(r_idx,c_idx):await self._update_game_display(game,interaction,content="遊戲結束！Gemini AI獲勝！");return
                else:print(f"{lp}GeminiChoseInvalidSpot:{gem_move_str} (internal {r_idx},{c_idx})")
            except Exception as e:print(f"{lp}ErrProcessingGeminiMove'{gem_move_str}':{e}")
        
        if not valid_mv: 
            print(f"{lp}GeminiFailValidMove.FallbackRandom.");game.last_ai_evaluation=(game.last_ai_evaluation or "")+"\n(因指令無效/錯誤,AI隨機下了一步)"
            es=[(r,c)for r in range(BOARD_SIZE)for c in range(BOARD_SIZE)if game.board[r][c]==EMPTY_SLOT_EMOJI]
            if es:
                r_f,c_f=random.choice(es); ai_fb_p=PLAYER_1_EMOJI if game.ai_plays_black else PLAYER_2_EMOJI
                if game.place_piece(r_f,c_f,ai_fb_p):print(f"{lp}Fallback random placed at internal ({r_f},{c_f})")
                else:print(f"{lp}CRITICAL: Fallback random move to ({r_f},{c_f}) also failed."); game.is_draw=True;game.game_over=True
                if game.check_for_win(r_f,c_f):await self._update_game_display(game,interaction,content="遊戲結束！Gemini AI(隨機)獲勝！");return
            else:game.is_draw=True;game.game_over=True
        
        if game.is_draw:await self._update_game_display(game,interaction,content="平局！");return
        if not game.game_over:game.switch_turn();await self._update_game_display(game,interaction)

    @gomoku_cmds.command(name="forfeit",description="放棄目前遊戲。")
    async def gomoku_forfeit(self,interaction:discord.Interaction): 
        lp="[DEBUG]/gomoku_forfeit:"; print(f"{lp}User:{interaction.user.id}")
        chid=interaction.channel_id
        if chid not in self.active_games or self.active_games[chid].game_over:
            await interaction.response.send_message("此頻道無遊戲可棄。",ephemeral=True); return
        game=self.active_games[chid]
        is_p=(interaction.user.id==game.player1_user.id)or \
             (not game.is_ai_game and game.player2_user and interaction.user.id==game.player2_user.id)
        if not is_p: await interaction.response.send_message("你非此遊戲玩家。",ephemeral=True); return

        if not interaction.response.is_done(): print(f"{lp}Deferring interaction {interaction.id}"); await interaction.response.defer()
        else: print(f"{lp}WARNING: Interaction {interaction.id} already responded before defer in forfeit.")

        game.game_over=True; forfeit_winner_display_name = "未知對手"
        
        if interaction.user.id == game.player1_user.id: # Player 1 forfeits
            game.winner = "Gemini AI" if game.is_ai_game else game.player2_user
            # Winner's piece is the piece AI/P2 was playing
            if game.is_ai_game: game.winner_piece = PLAYER_1_EMOJI if game.ai_plays_black else PLAYER_2_EMOJI
            else: game.winner_piece = PLAYER_2_EMOJI if game.p1_plays_black else PLAYER_1_EMOJI # P2's piece
            forfeit_winner_display_name = "Gemini AI" if game.is_ai_game else (game.player2_user.mention if game.player2_user else "對手")
        
        elif not game.is_ai_game and game.player2_user and interaction.user.id == game.player2_user.id: # Player 2 forfeits in PvP
            game.winner = game.player1_user
            game.winner_piece = PLAYER_1_EMOJI if game.p1_plays_black else PLAYER_2_EMOJI # P1's piece
            forfeit_winner_display_name = game.player1_user.mention
        else: 
            print(f"{lp}CRITICAL: Unexpected forfeit scenario."); game.winner="錯誤"; game.winner_piece="?" # Should not happen
        
        winner_piece_display = game.winner_piece or '?'
        final_content = f"{interaction.user.mention} 已棄權。{forfeit_winner_display_name} ({winner_piece_display}) 獲勝！"
        await self._update_game_display(game, interaction, content=final_content)
        if game.winner == "AI_PLACEHOLDER": game.winner = "Gemini AI" # Ensure consistency if placeholder was used

    @gomoku_cmds.command(name="board",description="顯示目前棋盤。")
    async def gomoku_board(self,interaction:discord.Interaction):
        lp="[DEBUG]/gomoku_board:";print(f"{lp}User:{interaction.user.id}")
        chid=interaction.channel_id
        if chid not in self.active_games:await interaction.response.send_message("此頻道最近沒有遊戲。",ephemeral=True);return
        game=self.active_games[chid]
        if game.game_message:
            try:
                await interaction.channel.fetch_message(game.game_message.id) 
                await interaction.response.send_message(f"目前的棋盤在這：{game.game_message.jump_url}",ephemeral=True);return
            except discord.NotFound:game.game_message=None
        if not interaction.response.is_done(): print(f"{lp}Deferring to send board.");await interaction.response.defer()
        await self._update_game_display(game,interaction,content="這是目前的棋盤：")

async def setup(bot: commands.Bot):
    await bot.add_cog(Gomoku(bot))
    print("Gomoku (五子棋) cog 已載入 (v.full_code_pvp_ai_isinstance_fix).")