from datetime import datetime, timezone, timedelta

import calendar
import string
import random

import discord
from redbot.core import Config, commands, modlog
from redbot.core.commands.requires import PrivilegeLevel


class WaterfallVerification(commands.Cog):
  """Waterfall Custom Verification cog, idk how it'll work yet."""

  default_guild_settings = {
    "VERIFICATION_CHANNEL": None,
    "VERIFICATION_ROLE": None,
    "UNVERIFIED_ROLE": None,
    "VERIFICATION_CODE_LENGTH": 6,
    "VERIFICATION_CODE_TYPE": "alphanumeric",
    "VERIFICATION_CODE_EXPIRY": 300,
    "VERIFICATION_IGNORED_ROLES": []
  }

  default_global_settings = default_guild_settings

  default_member_settings = {
    "verified": False,
    "verification_code": None,
    "code_expires_at": None,
    "verified_at": None
  }

  default_user_settings = default_member_settings

  def __init__(self, bot):
    super().__init__()
    self.bot = bot

    self.config = Config.get_conf(self, 0x77672e766572696679)  # wg.verify
    self.config.register_guild(**self.default_guild_settings)
    self.config.register_global(**self.default_global_settings)
    self.config.register_member(**self.default_member_settings)
    self.config.register_user(**self.default_user_settings)

  async def cog_load(self):
    await self.register_casetypes()

  @staticmethod
  async def register_casetypes():
    case_types = [
      {
        "name": "verify",
        "default_setting": True,
        "case_str": "Verify",
        "image": "<:verified:1280846920784547953>"
      },
      {
        "name": "unverify",
        "default_setting": True,
        "case_str": "Unverify",
        "image": ":x:"
      },
      {
        "name": "bypassverify",
        "default_setting": True,
        "case_str": "Bypassed Verification",
        "image": "<:verified_gold:1280846966716370995>"
      },
      {
        "name": "syncverify",
        "default_setting": True,
        "case_str": "Synced Verification Status",
        "image": ":arrows_counterclockwise:"
      }
    ]

    await modlog.register_casetypes(case_types)

  async def _verify_user(self, ctx, user: discord.Member, ignore_errors=False):
    """Verify a user. (internal function)"""
    verified = await self.config.member(user).verified()

    if verified:
      if ignore_errors:
        return
      return await ctx.send(embed=self._error_embed(f"{user.mention} is already verified."))
    else:
      # set the user as verified
      await self.config.member(user).verified.set(True)
      # set the time the user was verified
      await self.config.member(user).verified_at.set(datetime.now().timestamp())
      # add the verification role and remove the unverified role if set
      await user.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE()))
      if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
        await user.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))

  async def _unverify_user(self, ctx, user: discord.Member, ignore_errors=False):
    """Unverifies a member (internal function)"""
    verified = await self.config.member(user).verified()

    user_roles = [role for role in user.roles]
    ignored_roles = await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES()

    if not verified:
      if ignore_errors:
        return
      return await ctx.send(embed=self._error_embed(f"{user.mention} is not verified."))
    elif any(role.id in ignored_roles for role in user_roles):
      return await ctx.send(embed=self._error_embed(f"{user.mention} cannot be unverified due to their role permissions."))
    else:
      # remove verified status
      await self.config.member(user).verified.set(False)
      # remove verification timestamp
      await self.config.member(user).verified_at.set(None)
      # remove verification code
      await self.config.member(user).verification_code.set(None)
      # remove verification code expiry
      await self.config.member(user).code_expires_at.set(None)
      # remove the verification role
      await user.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE()))
      # add the unverified role if it exists
      if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
        await user.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))

  @staticmethod
  def _admin_info_embed(ctx, title: str, description: str, color):
    """Generate an info embed for an admin command."""
    info_embed = discord.Embed(
      title=title,
      description=description,
      color=color,
      timestamp=datetime.now(timezone.utc)
    )

    info_embed.set_footer(text=f"Action performed by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)

    return info_embed

  @staticmethod
  def _error_embed(description: str = "Oops...", title: str = "Error"):
    """Generate an error embed."""
    return discord.Embed(
      title=title,
      description=description,
      color=discord.Color.red()
    )

  @commands.group(name="verifyset")
  @commands.admin()
  async def command_verifyset(self, ctx):
    """Settings for the verification cog."""
    pass

  @command_verifyset.command(name="channel")
  async def command_verifyset_channel(self, ctx, channel: discord.TextChannel):
    """Set the verification channel. This is where users must run the verification command."""
    await self.config.guild(ctx.guild).VERIFICATION_CHANNEL.set(channel.id)
    await ctx.send(f"Verification channel set to {channel.mention}.")

  @command_verifyset.command(name="role")
  async def command_verifyset_role(self, ctx, role: discord.Role):
    """Set the verification role. This role will be given to users who have successfully verified."""
    await self.config.guild(ctx.guild).VERIFICATION_ROLE.set(role.id)
    await ctx.send(f"Verification role set to {role.mention}.")

  @command_verifyset.command(name="unverifiedrole")
  async def command_verifyset_unverifiedrole(self, ctx, role: discord.Role):
    """Set the unverified role. This role will be given to users who have not verified."""
    await self.config.guild(ctx.guild).UNVERIFIED_ROLE.set(role.id)
    await ctx.send(f"Unverified role set to {role.mention}.")

  @command_verifyset.group(name="code")
  async def command_verifyset_code(self, ctx):
    """Settings for verification codes."""
    pass

  @command_verifyset_code.command(name="length")
  async def command_verifyset_code_length(self, ctx, length: int):
    """Set the length of the verification code."""
    if length < 1:
      await ctx.send(embed=self._error_embed("The verification code length must be at least 1.", "Invalid Length"))
      return
    elif length > 32:
      await ctx.send(
        embed=self._error_embed("The verification code must not be longer than 32 characters.", "Invalid Length"))
      return
    await self.config.guild(ctx.guild).VERIFICATION_CODE_LENGTH.set(length)
    await ctx.send(f"Verification code length set to {length}.")

  @command_verifyset_code.command(name="type")
  async def command_verifyset_code_type(self, ctx, code_type: str):
    """Set whether the verification code should be alphanumeric."""
    # Check if the code type is valid
    if code_type not in ["alphanumeric", "numeric", "alphabetical"]:
      await ctx.send(
        embed=self._error_embed("The verification code type must be either alphanumeric, numeric or alphabetical.",
                                "Invalid Type"))
      return
    # update the config
    await self.config.guild(ctx.guild).VERIFICATION_CODE_TYPE.set(code_type)
    await ctx.send(f"Verification codes will now be {code_type}.")

  @command_verifyset_code.command(name="expiry")
  async def command_verifyset_code_expiry(self, ctx, expiry: int):
    """Set the expiry time for verification codes (in seconds)."""
    if expiry < 60 and expiry != 0:
      await ctx.send(embed=self._error_embed(
        "The expiry time for verification codes must be at least 60 seconds. (or 0 to disable expiry)"))
      return

    if expiry > 86400:
      await ctx.send(
        embed=self._error_embed("The expiry time for verification codes must be less than 86400 seconds (24 hours)."))
      return

    await self.config.guild(ctx.guild).VERIFICATION_CODE_EXPIRY.set(expiry)
    if expiry == 0:
      await ctx.send("Verification codes will no longer expire.")
    else:
      await ctx.send(f"Verification codes will now expire after {expiry} seconds.")

  @command_verifyset.group(name="ignoreroles")
  async def command_verifyset_ignoreroles(self, ctx):
    """Set roles that can bypass verification."""
    pass

  @command_verifyset_ignoreroles.command(name="add")
  async def command_verifyset_ignoreroles_add(self, ctx, role: discord.Role):
    """Allow a role to bypass verification."""
    ignored_roles = await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES()

    if role.id in ignored_roles:
      await ctx.send(embed=self._error_embed("That role already bypasses verification."))
      return

    ignored_roles.append(role.id)
    await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES.set(ignored_roles)
    await ctx.send(f"{role.mention} will now bypass verification.")

  @command_verifyset_ignoreroles.command(name="remove")
  async def command_verifyset_ignoreroles_remove(self, ctx, role: discord.Role):
    """Remove a role from being able to bypass verification."""
    ignored_roles = await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES()

    if role.id not in ignored_roles:
      await ctx.send(embed=self._error_embed("That role cannot bypass verification."))
      return

    ignored_roles.remove(role.id)
    await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES.set(ignored_roles)
    await ctx.send(f"{role.mention} will no longer bypass verification.")

  @command_verifyset_ignoreroles.command(name="list")
  async def command_verifyset_ignoreroles_list(self, ctx):
    """List the roles that can bypass verification."""
    ignored_roles = await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES()

    if not ignored_roles:
      await ctx.send(embed=self._error_embed("No roles can bypass verification."))
      return

    roles = [ctx.guild.get_role(role_id).mention for role_id in ignored_roles]
    await ctx.send(embed=discord.Embed(
      title="Ignored Roles",
      description="\n".join(roles),
      color=discord.Color.dark_gold()
    ))

  @commands.group(name="unverify")
  @commands.admin()
  async def command_unverify(self, ctx):
    """Unverify a user/users."""
    pass

  @command_unverify.command(name="user")
  async def command_unverify_user(self, ctx, user: discord.Member):
    """Unverify a user."""
    # skip if the user is already unverified
    if not await self.config.member(user).verified():
      await ctx.send(embed=self._error_embed(
        description=f"{user.mention} is not verified.\n\n"
                    f"Run `{ctx.prefix}syncverify user {user.id}` to refresh their verification status instead."
      ))
      return

    # unverify the user
    unverified_status = await self._unverify_user(ctx, user, ignore_errors=True)

    if unverified_status is not None:
      # since the user wasn't unverified, exit out of the function
      return

    info_embed = self._admin_info_embed(
      ctx=ctx,
      title="User Unverified",
      description=f"{user.mention} has been unverified.",
      color=discord.Color.dark_red()
    )

    case = await modlog.create_case(
      ctx.bot, ctx.guild, ctx.message.created_at, action_type="unverify",
      user=user, moderator=ctx.author, reason="Unverified by an administrator."
    )

    await ctx.send(embed=info_embed)

  @command_unverify.command(name="inactive")
  async def command_unverify_inactive(self, ctx, days: int, confirm_string: str = None):
    """DANGEROUS: Unverify users who haven't sent messages in a certain number of days."""
    if days < 60:
      await ctx.send(embed=self._error_embed("The number of days must be at least 60."))
      return

    if days > 730:
      await ctx.send(embed=self._error_embed(
        "The number of days must be less than 730.\nThis is to avoid encountering rate limits."))
      return

    confirm = confirm_string == "confirm"

    current_time = datetime.now(timezone.utc)
    inactive_time = current_time - timedelta(days=days)

    active_users = set()
    inactive_users = set()
    verified_role = ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE())

    # make the bot type while it's working
    async with ctx.typing():
      # iterate through all text channels in the server
      for channel in ctx.guild.text_channels:
        # check each message in the channel
        async for message in channel.history(after=inactive_time):
          if message.author.bot or message.author in active_users:
            continue
          active_users.add(message.author)

      ignore_roles = await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES()

      for member in verified_role.members:
        if member.bot:
          continue
        user_roles = [role for role in member.roles]
        if member not in active_users and not any(role.id in ignore_roles for role in user_roles):
          if confirm:
            # unverify the user if it's not a dry run
            await self._unverify_user(ctx, member, ignore_errors=True)
          inactive_users.add(member)

    info_embed = self._admin_info_embed(
      ctx=ctx,
      title="Inactive Users " +
            ("Unverified" if confirm else "Flagged for Unverification"),
      description=f"{len(inactive_users)} user{'s have' if len(inactive_users) != 1 else ' has'} been " +
                  (" unverified." if confirm else " flagged for unverification.\n\n"
                                                  "Please run the command again with `confirm` to complete the process."),
      color=discord.Color.dark_red() if confirm else discord.Color.dark_gold()
    )

    inactive_users = list(inactive_users)
    # alphabetical order :)
    inactive_users.sort(key=lambda x: x.display_name)

    # turn the list of users into columns of 12 users each

    info_embed.add_field(name="Users Flagged", value="\n".join([user.mention for user in inactive_users[:12]]), inline=True)

    while len(inactive_users) > 12:
      inactive_users = inactive_users[12:]
      info_embed.add_field(name=" ", value="\n".join([user.mention for user in inactive_users[:12]]), inline=True)

    await ctx.send(embed=info_embed)

  @commands.group(name="syncverify")
  @commands.admin()
  async def command_syncverify(self, ctx):
    """Refresh the verification status of a user/users."""
    pass

  @command_syncverify.command(name="all")
  async def command_syncverify_all(self, ctx):
    """DANGEROUS: Refresh the verification status of all users based on what the bot has configured."""
    verified_role = ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE())

    if verified_role is None:
      await ctx.send(embed=self._error_embed(
        "The verification role has not been set up. Please make sure this is configured before running the command."))
      return

    ignore_roles = await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES()

    async with ctx.typing():
      async for member in ctx.guild.fetch_members(limit=None):
        verified = await self.config.member(member).verified()

        user_roles = [role for role in member.roles]

        if any(role.id in ignore_roles for role in user_roles):
          # skip the user if they have a role that allows them to bypass verification
          continue

        if ctx.guild.owner_id == member.id:
          # skip the server owner
          continue

        if verified:
          # give the user the verified role and remove the unverified role
          await member.add_roles(verified_role)
          if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
            await member.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))
        else:
          # remove the verified role and add the unverified role
          await member.remove_roles(verified_role)
          if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
            await member.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))

    info_embed = self._admin_info_embed(
      ctx=ctx,
      title="User Verification Synced",
      description="All users' verification statuses have been synced.",
      color=discord.Color.dark_gold()
    )

    await ctx.send(embed=info_embed)

  @command_syncverify.command(name="user")
  async def command_syncverify_user(self, ctx, user: discord.Member):
    """Refresh the verification status of a user."""
    verified = await self.config.member(user).verified()

    if verified:
      # give the user the verified role and remove the unverified role
      await user.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE()))
      if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
        await user.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))
    else:
      # remove the verified role and add the unverified role
      await user.remove_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).VERIFICATION_ROLE()))
      if await self.config.guild(ctx.guild).UNVERIFIED_ROLE() is not None:
        await user.add_roles(ctx.guild.get_role(await self.config.guild(ctx.guild).UNVERIFIED_ROLE()))

    info_embed = self._admin_info_embed(
      ctx=ctx,
      title="User Verification Synced",
      description=f"{user.mention}'s verification status has been synced.",
      color=discord.Color.dark_gold()
    )

    case = await modlog.create_case(
      ctx.bot, ctx.guild, ctx.message.created_at, action_type="syncverify",
      user=user, moderator=ctx.author, reason="Verification status synced by an administrator."
    )

    await ctx.send(embed=info_embed)

  @commands.command(name="bypassverify")
  @commands.admin()
  async def command_bypassverify(self, ctx, user: discord.Member):
    """Bypass the verification process for a user."""

    # verify the user
    verify_status = await self._verify_user(ctx, user)

    if verify_status is not None:
      # since the user wasn't verified, exit out of the function
      return

    info_embed = self._admin_info_embed(
      ctx=ctx,
      title="Verification Bypassed",
      description=f"{user.mention} has been manually verified.",
      color=discord.Color.gold()
    )

    case = await modlog.create_case(
      ctx.bot, ctx.guild, ctx.message.created_at, action_type="bypassverify",
      user=user, moderator=ctx.author, reason="Manually verified by an administrator."
    )

    await ctx.send(embed=info_embed)

  @commands.command(name="verify")
  async def command_verify(self, ctx):
    """Verify yourself to gain access to the server."""

    # Check if the verification channel has been set up
    if await self.config.guild(ctx.guild).VERIFICATION_CHANNEL() is None:
      await ctx.send(
        embed=self._error_embed("The verification channel has not been set up. Please contact an administrator."))
      return

    # check if a verification role has been set up
    if await self.config.guild(ctx.guild).VERIFICATION_ROLE() is None:
      await ctx.send(
        embed=self._error_embed("The verification role has not been set up. Please contact an administrator."))
      return

    # check if the user is already verified
    if await self.config.member(ctx.author).verified():
      await ctx.send(embed=self._error_embed("You have already been verified."))
      return

    user_roles = [role for role in ctx.author.roles]
    ignored_roles = await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES()

    # check if the user has any roles that allow them to bypass verification
    if any(role.id in ignored_roles for role in user_roles):
      await self._verify_user(ctx, ctx.author)
      return await ctx.send(embed=discord.Embed(
        title="Verification Bypassed",
        description="You have been automatically verified due to your role permissions.",
        color=discord.Color.gold()
      ))

    verification_channel = ctx.guild.get_channel(await self.config.guild(ctx.guild).VERIFICATION_CHANNEL())

    if ctx.message.channel.id != verification_channel.id:
      await ctx.send(embed=self._error_embed(f"Please run the verification command in {verification_channel.mention}."))
      return

    current_time = calendar.timegm(ctx.message.created_at.utctimetuple())

    code_length = await self.config.guild(ctx.guild).VERIFICATION_CODE_LENGTH()
    code_type = await self.config.guild(ctx.guild).VERIFICATION_CODE_TYPE()
    code_expiry = await self.config.guild(ctx.guild).VERIFICATION_CODE_EXPIRY()
    expires_at = await self.config.member(ctx.author).code_expires_at()

    if code_type == "alphanumeric":
      char_pool = string.ascii_letters + string.digits
    elif code_type == "numeric":
      char_pool = string.digits
    elif code_type == "alphabetical":
      char_pool = string.ascii_letters
    else:
      # fallback if the code type is invalid
      char_pool = "!"

    code = await self.config.member(ctx.author).verification_code()
    # if the user doesn't have a code, generate a new one
    if code is None:
      code = "".join(random.choices(char_pool, k=code_length))
      await self.config.member(ctx.author).verification_code.set(code)
      await self.config.member(ctx.author).code_expires_at.set(ctx.message.created_at.timestamp() + code_expiry)

    # if the code has expired, generate a new one
    elif expires_at <= ctx.message.created_at.timestamp() and code_expiry != 0:
      code = "".join(random.choices(char_pool, k=code_length))
      await self.config.member(ctx.author).verification_code.set(code)
      await self.config.member(ctx.author).code_expires_at.set(ctx.message.created_at.timestamp() + code_expiry)

    expires_at = await self.config.member(ctx.author).code_expires_at()
    expires_at_timestamp = discord.utils.format_dt(
      datetime.now(timezone.utc) + timedelta(seconds=expires_at - current_time), "R"
    )

    message = f"Your verification code is: `{code}`\n\n" \
              + f"Please send a message containing __only__ this code in {verification_channel.mention}.\n\n" \
              + (
                f"This code will expire {expires_at_timestamp}, so make sure you verify quickly!" if code_expiry != 0 else '')

    verification_embed = discord.Embed(
      title="Verification Code",
      description=message,
      color=discord.Color.blue(),
      timestamp=ctx.message.created_at,
    )

    verification_embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url)

    try:
      await ctx.author.send(embed=verification_embed)
    except discord.errors.Forbidden:
      error_message = await ctx.send(embed=self._error_embed(
        "Couldn't send you a verification code in DMs. Please make sure you have DMs from server members enabled."
      ))
      await error_message.delete(delay=10.0)
    finally:
      await ctx.message.delete(delay=5.0)

  @commands.command(name="verifyinfo")
  async def command_verifyinfo(self, ctx, user: discord.Member = None):
    """Get information about a user's verification status."""

    if user is None:
      user = ctx.author

    if not ctx.author.guild_permissions.administrator and user.id != ctx.author.id:
      await ctx.send(embed=self._error_embed(
        title="Permission Error",
        description="You must be an administrator to view another user's verification status."
      ))
      return

    verified = await self.config.member(user).verified()
    verified_at = await self.config.member(user).verified_at()

    ignore_roles = await self.config.guild(ctx.guild).VERIFICATION_IGNORED_ROLES()
    user_roles = [role for role in user.roles]

    bypass = any(role.id in ignore_roles for role in user_roles)

    if bypass:
      status = " <:verified_gold:1280846966716370995> Bypasses Verification"
    elif verified:
      status = "<:verified:1280846920784547953> Verified"
    else:
      status = ":x: Unverified"

    if verified_at is not None:
      verified_at = "%s (%s)" % (
        discord.utils.format_dt(datetime.fromtimestamp(verified_at), "F"),
        discord.utils.format_dt(datetime.fromtimestamp(verified_at), "R")
      )

    embed = discord.Embed(
      title=f"{user.display_name}'s Verification Status",
      description=f"User: {user.mention}",
      color=discord.Color.dark_green() if verified else discord.Color.gold() if bypass else discord.Color.red(),
    )

    embed.add_field(name="Status", value=status, inline=False)

    if verified_at is not None:
      embed.add_field(name="Verified At", value=verified_at, inline=False)

    if not verified and not bypass:
      verification_code = await self.config.member(user).verification_code()
      code_expires_at = await self.config.member(user).code_expires_at()

      embed.add_field(name="Verification Code",
                      value=verification_code if verification_code is not None else "N/A",
                      inline=True
                      )

      embed.add_field(name="Code Expires At",
                      value=discord.utils.format_dt(
                        datetime.fromtimestamp(code_expires_at), "F"
                      ) if code_expires_at is not None else "N/A",
                      inline=True
                      )

    embed.set_thumbnail(url=user.avatar.url)

    await ctx.send(embed=embed)

  @commands.Cog.listener(name="on_message")
  async def listen_for_verification_codes(self, message):
    if message.author.bot:
      return

    if not message.guild:
      return

    if await self.config.guild(message.guild).VERIFICATION_CHANNEL() is None:
      return

    if message.channel.id != await self.config.guild(message.guild).VERIFICATION_CHANNEL():
      return

    author = message.author
    code = await self.config.member(author).verification_code()
    code_expiry = await self.config.guild(message.guild).VERIFICATION_CODE_EXPIRY()
    expires_at = await self.config.member(author).code_expires_at()

    if code is None:
      return

    if message.content.strip() == code:
      # check if the code has expired
      if expires_at <= message.created_at.timestamp() and code_expiry != 0:
        await message.channel.send(embed=self._error_embed(
          "That verification code has expired. Please run the verification command again to generate a "
          "new code."
        ))
        return
      # ok, the code matches now
      else:
        await self._verify_user(message, author)

        verified_message = await message.reply(embed=discord.Embed(
          title="Verification Success",
          description=f"You have been verified! Welcome to **{message.guild.name}**!",
          color=discord.Color.green()
        ),
          mention_author=True
        )

        case = await modlog.create_case(
          self.bot, message.guild, message.created_at, action_type="verify",
          user=author, moderator=self.bot.user, reason="Verified through the verification channel."
        )

        # delete the verification message after a few seconds
        await verified_message.delete(delay=5.0)
        await message.delete(delay=7.5)

  @commands.Cog.listener(name="on_member_join")
  async def unverifed_role_new_members(self, member):
    """Give new members the unverified role when they join the server."""
    if await self.config.member(member).verified():
      return

    if await self.config.guild(member.guild).UNVERIFIED_ROLE() is not None:
      await member.add_roles(member.guild.get_role(await self.config.guild(member.guild).UNVERIFIED_ROLE()))
